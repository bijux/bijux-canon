# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed operation adapters backed by installed canonical package services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Protocol

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexService,
    LexicalIndexChunk,
    LexicalIndexLimits,
    build_lexical_index_segment,
)
from bijux_canon_index.infra.embeddings.local_model import EmbeddedBatch
from bijux_canon_ingest.application.canonical_ingest import (
    CanonicalIngestRequest,
    CanonicalIngestRuntime,
    assemble_corpus_snapshot_manifest,
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshotConfiguration

from bijux_canon_runtime.model.artifact import AddressedArtifact, canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


class CanonicalEmbeddingService(Protocol):
    """Required locked local embedding behavior for Runtime composition."""

    @property
    def model_lock_id(self) -> str:
        """Return the exact model lock identity."""
        ...

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        """Embed canonical nonempty text in caller order."""
        ...


@dataclass(frozen=True, slots=True)
class _IndexableChunk:
    chunk_id: str
    document_id: str
    ordinal: int
    text: str
    metadata: dict[str, object]


def _json_object(artifact: AddressedArtifact, contract_id: str) -> dict[str, object]:
    if artifact.descriptor.schema_id != contract_id:
        raise StepDispatchError("loaded artifact does not match its input contract")
    if artifact.descriptor.media_type != "application/json":
        raise StepDispatchError("operation input must be canonical JSON")
    try:
        value = json.loads(artifact.canonical_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StepDispatchError("operation input JSON is unreadable") from error
    if not isinstance(value, dict):
        raise StepDispatchError("operation input must be a JSON object")
    return value


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def _artifact_input(
    *,
    store: ArtifactPayloadStore,
    upstream: tuple[StepOutputArtifact, ...],
    contract_id: str,
    fallback_id: ArtifactID | None,
) -> AddressedArtifact:
    selected = tuple(item for item in upstream if item.contract_id == contract_id)
    if len(selected) == 1:
        return selected[0].artifact
    if selected:
        raise StepDispatchError("operation input artifact is ambiguous")
    if fallback_id is None:
        raise StepDispatchError(f"operation input is unavailable: {contract_id}")
    try:
        artifact = store.load(fallback_id)
    except (KeyError, ValueError) as error:
        raise StepDispatchError(
            f"operation input artifact cannot be loaded: {fallback_id}"
        ) from error
    if artifact.descriptor.schema_id != contract_id:
        raise StepDispatchError("loaded artifact does not match its input contract")
    return artifact


def _bounded_output(
    *,
    step: ConcreteDagStep,
    contract_id: str,
    media_type: str,
    payload: bytes,
    upstream: tuple[StepOutputArtifact, ...],
    external_dependencies: tuple[ArtifactID, ...] = (),
) -> tuple[StepOutputArtifact, ...]:
    if len(payload) > step.inputs.budget.max_artifact_bytes:
        raise StepDispatchError(
            f"{contract_id} exceeds the request artifact byte budget"
        )
    return (
        StepOutputArtifact.from_payload(
            step=step,
            contract_id=contract_id,
            media_type=media_type,
            payload=payload,
            dependencies=upstream,
            dependency_artifact_ids=external_dependencies,
        ),
    )


def _validated_snapshot(payload: dict[str, object]) -> dict[str, object]:
    if payload.get("schema_version") != "bijux.canon.ingest.corpus_snapshot.v1":
        raise StepDispatchError("corpus snapshot schema is unsupported")
    identity = payload.get("snapshot_id")
    body = dict(payload)
    body.pop("snapshot_id", None)
    if identity != _identity(body):
        raise StepDispatchError("corpus snapshot identity is invalid")
    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise StepDispatchError("corpus snapshot has no admitted documents")
    return payload


def _indexable_chunks(snapshot: dict[str, object]) -> tuple[_IndexableChunk, ...]:
    raw_documents = snapshot["documents"]
    assert isinstance(raw_documents, list)
    result: list[_IndexableChunk] = []
    try:
        for raw_document in raw_documents:
            if not isinstance(raw_document, dict):
                raise TypeError
            document_id = raw_document["document_id"]
            metadata = raw_document["metadata"]
            chunks = raw_document["chunks"]
            if (
                not isinstance(document_id, str)
                or not isinstance(metadata, dict)
                or not isinstance(chunks, list)
            ):
                raise TypeError
            source_uri = metadata.get("canonical_uri")
            if not isinstance(source_uri, str) or not source_uri:
                source_uri = f"urn:bijux:source:{metadata['source_content_sha256']}"
            for raw_chunk in chunks:
                if not isinstance(raw_chunk, dict):
                    raise TypeError
                chunk_id = raw_chunk["chunk_id"]
                ordinal = raw_chunk["chunk_index"]
                text = raw_chunk["normalized_text"]
                text_sha256 = raw_chunk["normalized_text_sha256"]
                if (
                    not isinstance(chunk_id, str)
                    or isinstance(ordinal, bool)
                    or not isinstance(ordinal, int)
                    or not isinstance(text, str)
                    or not isinstance(text_sha256, str)
                    or hashlib.sha256(text.encode("utf-8")).hexdigest() != text_sha256
                ):
                    raise ValueError
                index_metadata: dict[str, object] = {
                    "format": metadata["format_id"],
                    "path": metadata["relative_path"],
                    "source_id": document_id,
                    "source_text_sha256": text_sha256,
                    "source_uri": source_uri,
                }
                for source_name, target_name in (
                    ("doi", "doi"),
                    ("language", "language"),
                    ("publication_date", "date"),
                ):
                    value = metadata.get(source_name)
                    if isinstance(value, str) and value:
                        index_metadata[target_name] = value
                section_paths = raw_chunk.get("section_paths")
                if isinstance(section_paths, list) and section_paths:
                    first = section_paths[0]
                    if isinstance(first, list) and all(
                        isinstance(item, str) and item for item in first
                    ):
                        index_metadata["section"] = " / ".join(first)
                result.append(
                    _IndexableChunk(
                        chunk_id,
                        document_id,
                        ordinal,
                        text,
                        index_metadata,
                    )
                )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("corpus snapshot chunk records are invalid") from error
    result.sort(key=lambda item: item.chunk_id)
    if not result or len({item.chunk_id for item in result}) != len(result):
        raise StepDispatchError("corpus snapshot chunk identities are invalid")
    return tuple(result)


class CanonicalIngestOperationAdapter:
    """Discover, admit, extract, and chunk one local source directory."""

    adapter_id = "bijux-canon-ingest:corpus-preparation:v1"
    adapter_version = "1.0"
    operation = DagOperation.INGEST

    def __init__(self, runtime: CanonicalIngestRuntime | None = None) -> None:
        self._runtime = runtime or CanonicalIngestRuntime()

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if upstream_artifacts or step.inputs.source_directory is None:
            raise StepDispatchError("ingest requires one local source directory")
        source = Path(step.inputs.source_directory)
        root_name = source.name or "corpus"
        corpus_name = root_name.casefold()
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,127}", corpus_name) is None:
            corpus_name = f"corpus-{hashlib.sha256(root_name.encode()).hexdigest()[:16]}"
        preparation = self._runtime.prepare(
            CanonicalIngestRequest(
                root_path=source,
                root_name=root_name,
                configuration=CorpusSnapshotConfiguration(corpus_name),
            )
        )
        payload = canonical_json_bytes(preparation.manifest())
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="ingest.source-documents.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


class CanonicalSnapshotOperationAdapter:
    """Assemble one immutable snapshot manifest from prepared documents."""

    adapter_id = "bijux-canon-ingest:corpus-snapshot:v1"
    adapter_version = "1.0"
    operation = DagOperation.SNAPSHOT

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if len(upstream_artifacts) != 1:
            raise StepDispatchError("snapshot requires one preparation artifact")
        preparation = _json_object(
            upstream_artifacts[0].artifact,
            "ingest.source-documents.v1",
        )
        snapshot = assemble_corpus_snapshot_manifest(preparation)
        payload = canonical_json_bytes(snapshot)
        return _bounded_output(
            step=step,
            contract_id="ingest.corpus-snapshot.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
        )


class CanonicalEmbeddingOperationAdapter:
    """Create a locked embedding matrix from one persisted snapshot."""

    adapter_id = "bijux-canon-index:embedding-matrix:v1"
    adapter_version = "1.0"
    operation = DagOperation.EMBED

    def __init__(
        self,
        *,
        store: ArtifactPayloadStore,
        embedding: CanonicalEmbeddingService,
    ) -> None:
        self._store = store
        self._embedding = embedding

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        snapshot_artifact = _artifact_input(
            store=self._store,
            upstream=upstream_artifacts,
            contract_id="ingest.corpus-snapshot.v1",
            fallback_id=step.inputs.corpus_id,
        )
        snapshot = _validated_snapshot(
            _json_object(snapshot_artifact, "ingest.corpus-snapshot.v1")
        )
        chunks = _indexable_chunks(snapshot)
        batch = self._embedding.embed(tuple(item.text for item in chunks))
        if batch.model_lock_id != self._embedding.model_lock_id:
            raise StepDispatchError("embedding result changed model lock identity")
        if len(batch.vectors) != len(chunks):
            raise StepDispatchError("embedding result count does not match chunks")
        payload = canonical_json_bytes(
            {
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "metadata": chunk.metadata,
                        "ordinal": chunk.ordinal,
                        "text": chunk.text,
                        "vector": list(vector),
                    }
                    for chunk, vector in zip(chunks, batch.vectors, strict=True)
                ],
                "dimension": len(batch.vectors[0]),
                "model_lock_artifact_id": batch.model_lock_id,
                "schema_version": "bijux.canon.index.embedding_matrix.v1",
                "snapshot_artifact_id": str(
                    snapshot_artifact.descriptor.artifact_id
                ),
                "snapshot_id": snapshot["snapshot_id"],
            }
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="index.embedding-matrix.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
            external_dependencies=(
                ()
                if upstream_artifacts
                else (snapshot_artifact.descriptor.artifact_id,)
            ),
        )


class CanonicalLexicalIndexOperationAdapter:
    """Build exactly one persistent SQLite FTS5 segment from a snapshot."""

    adapter_id = "bijux-canon-index:lexical-segment:v1"
    adapter_version = "1.0"
    operation = DagOperation.LEXICAL_INDEX

    def __init__(self, *, store: ArtifactPayloadStore, working_root: Path) -> None:
        self._store = store
        self._working_root = working_root

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        snapshot_artifact = _artifact_input(
            store=self._store,
            upstream=upstream_artifacts,
            contract_id="ingest.corpus-snapshot.v1",
            fallback_id=step.inputs.corpus_id,
        )
        snapshot = _validated_snapshot(
            _json_object(snapshot_artifact, "ingest.corpus-snapshot.v1")
        )
        chunks = _indexable_chunks(snapshot)
        self._working_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".lexical-operation-",
            dir=self._working_root,
        ) as work:
            destination = Path(work) / "lexical.sqlite"
            build_lexical_index_segment(
                destination,
                (
                    LexicalIndexChunk(
                        item.chunk_id,
                        item.document_id,
                        item.ordinal,
                        item.text,
                        item.metadata,
                    )
                    for item in chunks
                ),
                limits=LexicalIndexLimits(
                    max_chunks=len(chunks),
                    max_text_bytes=sum(len(item.text.encode("utf-8")) for item in chunks),
                    max_metadata_bytes=step.inputs.budget.max_artifact_bytes,
                ),
            )
            payload = destination.read_bytes()
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="index.lexical.v1",
            media_type="application/vnd.sqlite3",
            payload=payload,
            upstream=upstream_artifacts,
            external_dependencies=(
                ()
                if upstream_artifacts
                else (snapshot_artifact.descriptor.artifact_id,)
            ),
        )


class CanonicalDenseIndexOperationAdapter:
    """Build dense segments and publish one complete portable index generation."""

    adapter_id = "bijux-canon-index:composite-generation:v1"
    adapter_version = "1.0"
    operation = DagOperation.DENSE_INDEX

    def __init__(
        self,
        *,
        index: IndexService,
        working_root: Path,
    ) -> None:
        self._index = index
        self._working_root = working_root

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if {item.contract_id for item in upstream_artifacts} != {
            "index.embedding-matrix.v1",
            "index.lexical.v1",
        }:
            raise StepDispatchError("dense indexing requires matrix and lexical inputs")
        matrix_artifact = next(
            item.artifact
            for item in upstream_artifacts
            if item.contract_id == "index.embedding-matrix.v1"
        )
        lexical_artifact = next(
            item.artifact
            for item in upstream_artifacts
            if item.contract_id == "index.lexical.v1"
        )
        matrix = _json_object(matrix_artifact, "index.embedding-matrix.v1")
        chunks, model_lock_id, snapshot_artifact_id = _matrix_chunks(matrix)
        self._working_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".dense-operation-",
            dir=self._working_root,
        ) as work:
            lexical_path = Path(work) / "lexical.sqlite"
            lexical_path.write_bytes(lexical_artifact.canonical_bytes)
            report = self._index.build_from_lexical(
                lexical_path,
                chunks,
                snapshot_artifact_id=snapshot_artifact_id,
                model_lock_artifact_id=model_lock_id,
                limits=IndexBuildLimits(
                    max_chunks=len(chunks),
                    max_text_bytes=sum(len(item.text.encode("utf-8")) for item in chunks),
                    max_vector_bytes=sum(len(item.vector) * 4 for item in chunks),
                    max_metadata_bytes=step.inputs.budget.max_artifact_bytes,
                ),
                activate=True,
            )
        archive = self._index.export(report.generation_id)
        payload = archive.canonical_bytes
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="index.composite.v1",
            media_type="application/vnd.bijux.index-generation+json",
            payload=payload,
            upstream=upstream_artifacts,
        )


def _matrix_chunks(
    matrix: Mapping[str, object],
) -> tuple[tuple[AdmittedIndexChunk, ...], str, str]:
    if matrix.get("schema_version") != "bijux.canon.index.embedding_matrix.v1":
        raise StepDispatchError("embedding matrix schema is unsupported")
    raw_chunks = matrix.get("chunks")
    model_lock_id = matrix.get("model_lock_artifact_id")
    snapshot_artifact_id = matrix.get("snapshot_artifact_id")
    if (
        not isinstance(raw_chunks, list)
        or not raw_chunks
        or not isinstance(model_lock_id, str)
        or not isinstance(snapshot_artifact_id, str)
    ):
        raise StepDispatchError("embedding matrix fields are invalid")
    chunks: list[AdmittedIndexChunk] = []
    try:
        for raw in raw_chunks:
            if not isinstance(raw, dict):
                raise TypeError
            vector = raw["vector"]
            metadata = raw["metadata"]
            if not isinstance(vector, list) or not isinstance(metadata, dict):
                raise TypeError
            chunks.append(
                AdmittedIndexChunk(
                    chunk_id=str(raw["chunk_id"]),
                    document_id=str(raw["document_id"]),
                    ordinal=int(raw["ordinal"]),
                    text=str(raw["text"]),
                    vector=tuple(float(item) for item in vector),
                    metadata=metadata,
                )
            )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError("embedding matrix chunk records are invalid") from error
    dimension = matrix.get("dimension")
    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
        raise StepDispatchError("embedding matrix dimension is invalid")
    if any(len(item.vector) != dimension for item in chunks):
        raise StepDispatchError("embedding matrix vector dimensions diverge")
    return tuple(chunks), model_lock_id, snapshot_artifact_id


__all__ = [
    "CanonicalDenseIndexOperationAdapter",
    "CanonicalEmbeddingOperationAdapter",
    "CanonicalEmbeddingService",
    "CanonicalIngestOperationAdapter",
    "CanonicalLexicalIndexOperationAdapter",
    "CanonicalSnapshotOperationAdapter",
]
