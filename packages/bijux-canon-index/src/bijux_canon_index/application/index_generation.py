# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Build coherent lexical and dense indexes from one admitted snapshot."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Protocol

from bijux_canon_index.domain.metadata_filters import (
    MetadataValue,
    validated_metadata,
)
from bijux_canon_index.infra.adapters.faiss.exact import (
    DenseVectorRecord,
    FaissExactIndex,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import (
    FaissHnswIndex,
    HnswParameters,
)
from bijux_canon_index.infra.adapters.sqlite.lexical import (
    LexicalChunk,
    SQLiteLexicalIndex,
)

SCHEMA_VERSION = 1
MANIFEST_NAME = "generation.json"
LEXICAL_NAME = "lexical.sqlite"
EXACT_NAME = "dense-exact.sqlite"
HNSW_NAME = "dense-hnsw.sqlite"


class _SegmentManifest(Protocol):
    @property
    def generation_id(self) -> str: ...

    @property
    def chunk_set_sha256(self) -> str: ...


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class AdmittedIndexChunk:
    """One snapshot chunk paired with its locked-model vector."""

    chunk_id: str
    document_id: str
    ordinal: int
    text: str
    vector: Sequence[float]
    metadata: Mapping[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class LexicalIndexChunk:
    """One snapshot chunk admitted without requiring an embedding vector."""

    chunk_id: str
    document_id: str
    ordinal: int
    text: str
    metadata: Mapping[str, MetadataValue]


@dataclass(frozen=True, slots=True)
class LexicalIndexLimits:
    """Hard admission bounds for an independent lexical segment build."""

    max_chunks: int
    max_text_bytes: int
    max_metadata_bytes: int

    def __post_init__(self) -> None:
        if min(self.max_chunks, self.max_text_bytes, self.max_metadata_bytes) <= 0:
            raise ValueError("all lexical index limits must be positive")


@dataclass(frozen=True, slots=True)
class IndexBuildLimits:
    """Hard admission bounds for an in-memory generation build."""

    max_chunks: int
    max_text_bytes: int
    max_vector_bytes: int
    max_metadata_bytes: int

    def __post_init__(self) -> None:
        if min(
            self.max_chunks,
            self.max_text_bytes,
            self.max_vector_bytes,
            self.max_metadata_bytes,
        ) <= 0:
            raise ValueError("all index build limits must be positive")


@dataclass(frozen=True, slots=True)
class IndexBuildStatistics:
    """Exact admitted resource use bound into the generation identity."""

    chunk_count: int
    text_bytes: int
    vector_bytes: int
    metadata_bytes: int
    dimension: int

    def __post_init__(self) -> None:
        if self.chunk_count <= 0 or self.dimension <= 0:
            raise ValueError("index build statistics require chunks and a dimension")
        if min(self.text_bytes, self.vector_bytes, self.metadata_bytes) < 0:
            raise ValueError("index build byte statistics must not be negative")


@dataclass(frozen=True, slots=True)
class IndexBuildStageReceipt:
    """Verified identity of one completed persistent index segment."""

    stage: str
    backend: str
    file_name: str
    file_sha256: str
    segment_generation_id: str
    chunk_set_sha256: str
    item_count: int

    def __post_init__(self) -> None:
        if self.item_count <= 0:
            raise ValueError("index stage receipts require a positive item count")
        if not all(
            (
                self.stage,
                self.backend,
                self.file_name,
                self.file_sha256,
                self.segment_generation_id,
                self.chunk_set_sha256,
            )
        ):
            raise ValueError("index stage receipt identities must not be empty")


@dataclass(frozen=True, slots=True)
class IndexGenerationLineage:
    """Content-bound parent and delta identity for a derived generation."""

    parent_generation_id: str
    delta_sha256: str
    added: int
    modified: int
    deleted: int
    tombstoned: int

    def __post_init__(self) -> None:
        if not self.parent_generation_id or not self.delta_sha256:
            raise ValueError("index generation lineage identities must not be empty")
        if min(self.added, self.modified, self.deleted, self.tombstoned) < 0:
            raise ValueError("index generation lineage counts must not be negative")
        if self.added + self.modified + self.deleted + self.tombstoned == 0:
            raise ValueError("index generation lineage requires a non-empty delta")


@dataclass(frozen=True, slots=True)
class IndexGenerationManifest:
    """Identity and receipts for one coherent three-segment generation."""

    schema_version: int
    generation_id: str
    snapshot_artifact_id: str
    model_lock_artifact_id: str
    limits: IndexBuildLimits
    statistics: IndexBuildStatistics
    hnsw_parameters: HnswParameters
    chunk_set_sha256: str
    stages: tuple[IndexBuildStageReceipt, ...]
    lineage: IndexGenerationLineage | None = None


class IndexGenerationBuildError(RuntimeError):
    """A named build stage failed before coherent publication."""

    def __init__(
        self,
        stage: str,
        completed_stages: Sequence[IndexBuildStageReceipt],
        cause: BaseException,
    ) -> None:
        self.stage = stage
        self.completed_stages = tuple(completed_stages)
        self.cause = cause
        super().__init__(f"index generation stage {stage!r} failed: {cause}")


class IndexGenerationIntegrityError(ValueError):
    """A stored generation envelope or cross-segment invariant is invalid."""


def _manifest_payload(manifest: IndexGenerationManifest) -> dict[str, object]:
    return {
        "chunk_set_sha256": manifest.chunk_set_sha256,
        "generation_id": manifest.generation_id,
        "hnsw_parameters": asdict(manifest.hnsw_parameters),
        "limits": asdict(manifest.limits),
        "lineage": None if manifest.lineage is None else asdict(manifest.lineage),
        "model_lock_artifact_id": manifest.model_lock_artifact_id,
        "schema_version": manifest.schema_version,
        "snapshot_artifact_id": manifest.snapshot_artifact_id,
        "stages": [asdict(receipt) for receipt in manifest.stages],
        "statistics": asdict(manifest.statistics),
    }


def _generation_id(payload: Mapping[str, object]) -> str:
    identity = dict(payload)
    identity.pop("generation_id", None)
    return f"sha256:{_sha256_bytes(_canonical_json(identity).encode('utf-8'))}"


def _parse_manifest(payload: object) -> IndexGenerationManifest:
    if not isinstance(payload, dict):
        raise ValueError("index generation manifest must be a JSON object")
    expected = {
        "chunk_set_sha256",
        "generation_id",
        "hnsw_parameters",
        "limits",
        "lineage",
        "model_lock_artifact_id",
        "schema_version",
        "snapshot_artifact_id",
        "stages",
        "statistics",
    }
    if set(payload) != expected:
        raise ValueError("index generation manifest fields are unsupported")
    try:
        stages_payload = payload["stages"]
        if not isinstance(stages_payload, list):
            raise TypeError("stages must be a list")
        lineage_payload = payload["lineage"]
        lineage = (
            None
            if lineage_payload is None
            else IndexGenerationLineage(**lineage_payload)
        )
        manifest = IndexGenerationManifest(
            schema_version=int(payload["schema_version"]),
            generation_id=str(payload["generation_id"]),
            snapshot_artifact_id=str(payload["snapshot_artifact_id"]),
            model_lock_artifact_id=str(payload["model_lock_artifact_id"]),
            limits=IndexBuildLimits(**payload["limits"]),
            statistics=IndexBuildStatistics(**payload["statistics"]),
            hnsw_parameters=HnswParameters(**payload["hnsw_parameters"]),
            chunk_set_sha256=str(payload["chunk_set_sha256"]),
            stages=tuple(IndexBuildStageReceipt(**item) for item in stages_payload),
            lineage=lineage,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("index generation manifest is invalid") from error
    if manifest.schema_version != SCHEMA_VERSION:
        raise ValueError("index generation manifest schema is unsupported")
    if not manifest.snapshot_artifact_id or not manifest.model_lock_artifact_id:
        raise ValueError("index generation input identities must not be empty")
    if manifest.generation_id != _generation_id(payload):
        raise ValueError("index generation identity does not match its manifest")
    return manifest


def _admit_chunks(
    chunks: Iterable[AdmittedIndexChunk], limits: IndexBuildLimits
) -> tuple[tuple[AdmittedIndexChunk, ...], IndexBuildStatistics]:
    admitted: list[AdmittedIndexChunk] = []
    text_bytes = 0
    vector_bytes = 0
    metadata_bytes = 0
    dimension: int | None = None
    for source in chunks:
        if len(admitted) >= limits.max_chunks:
            raise ValueError("index build exceeds max_chunks")
        if not source.chunk_id or not source.document_id:
            raise ValueError("chunk and document identities must not be empty")
        if source.ordinal < 0 or not source.text:
            raise ValueError("index chunks require non-negative ordinals and text")
        vector = tuple(float(value) for value in source.vector)
        if not vector or any(not math.isfinite(value) for value in vector):
            raise ValueError("index vectors must be non-empty and finite")
        if dimension is None:
            dimension = len(vector)
        elif len(vector) != dimension:
            raise ValueError("all index vectors must have the same dimension")
        metadata = validated_metadata(source.metadata)
        text_bytes += len(source.text.encode("utf-8"))
        vector_bytes += len(vector) * 4
        metadata_bytes += len(_canonical_json(dict(metadata)).encode("utf-8"))
        if text_bytes > limits.max_text_bytes:
            raise ValueError("index build exceeds max_text_bytes")
        if vector_bytes > limits.max_vector_bytes:
            raise ValueError("index build exceeds max_vector_bytes")
        if metadata_bytes > limits.max_metadata_bytes:
            raise ValueError("index build exceeds max_metadata_bytes")
        admitted.append(
            AdmittedIndexChunk(
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                ordinal=source.ordinal,
                text=source.text,
                vector=vector,
                metadata=metadata,
            )
        )
    if not admitted:
        raise ValueError("an index generation requires at least one admitted chunk")
    admitted.sort(key=lambda chunk: chunk.chunk_id)
    identities = [chunk.chunk_id for chunk in admitted]
    if len(identities) != len(set(identities)):
        raise ValueError("chunk identities must be unique within a generation")
    return tuple(admitted), IndexBuildStatistics(
        chunk_count=len(admitted),
        text_bytes=text_bytes,
        vector_bytes=vector_bytes,
        metadata_bytes=metadata_bytes,
        dimension=dimension or 0,
    )


def _admit_lexical_chunks(
    chunks: Iterable[LexicalIndexChunk], limits: LexicalIndexLimits
) -> tuple[LexicalChunk, ...]:
    admitted: list[LexicalChunk] = []
    text_bytes = 0
    metadata_bytes = 0
    for source in chunks:
        if len(admitted) >= limits.max_chunks:
            raise ValueError("lexical index build exceeds max_chunks")
        metadata = validated_metadata(source.metadata)
        text_bytes += len(source.text.encode("utf-8"))
        metadata_bytes += len(_canonical_json(dict(metadata)).encode("utf-8"))
        if text_bytes > limits.max_text_bytes:
            raise ValueError("lexical index build exceeds max_text_bytes")
        if metadata_bytes > limits.max_metadata_bytes:
            raise ValueError("lexical index build exceeds max_metadata_bytes")
        admitted.append(
            LexicalChunk(
                chunk_id=source.chunk_id,
                document_id=source.document_id,
                ordinal=source.ordinal,
                text=source.text,
                metadata=metadata,
            )
        )
    if not admitted:
        raise ValueError("a lexical index segment requires at least one admitted chunk")
    admitted.sort(key=lambda chunk: chunk.chunk_id)
    identities = [chunk.chunk_id for chunk in admitted]
    if len(identities) != len(set(identities)):
        raise ValueError("chunk identities must be unique within a lexical segment")
    return tuple(admitted)


def build_lexical_index_segment(
    path: str | Path,
    chunks: Iterable[LexicalIndexChunk],
    *,
    limits: LexicalIndexLimits,
) -> IndexBuildStageReceipt:
    """Build one bounded lexical segment without performing dense work."""

    admitted = _admit_lexical_chunks(chunks, limits)
    destination = Path(path).resolve()
    with SQLiteLexicalIndex.build(destination, admitted) as lexical:
        return _stage_receipt(
            "lexical",
            "sqlite-fts5",
            destination,
            lexical.manifest.generation_id,
            lexical.manifest.chunk_set_sha256,
            lexical.manifest.chunk_count,
        )


class IndexGeneration:
    """Verified read handles for one coherent persistent index generation."""

    def __init__(
        self,
        path: Path,
        manifest: IndexGenerationManifest,
        lexical: SQLiteLexicalIndex,
        exact: FaissExactIndex,
        hnsw: FaissHnswIndex,
    ) -> None:
        self.path = path
        self.manifest = manifest
        self.lexical = lexical
        self.exact = exact
        self.hnsw = hnsw

    @classmethod
    def open(cls, path: str | Path) -> IndexGeneration:
        """Open and verify a generation manifest and every referenced segment."""

        root = Path(path).resolve()
        manifest_path = root / MANIFEST_NAME
        try:
            raw = manifest_path.read_bytes()
        except FileNotFoundError as error:
            if not root.is_dir():
                raise
            raise IndexGenerationIntegrityError(
                "index generation manifest is unavailable"
            ) from error
        except OSError as error:
            raise IndexGenerationIntegrityError(
                "index generation manifest is unavailable"
            ) from error
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise IndexGenerationIntegrityError(
                "index generation manifest is unreadable"
            ) from error
        try:
            manifest = _parse_manifest(payload)
        except ValueError as error:
            raise IndexGenerationIntegrityError(str(error)) from error
        if raw != (_canonical_json(payload) + "\n").encode("utf-8"):
            raise IndexGenerationIntegrityError(
                "index generation manifest is not canonical JSON"
            )
        receipts = {receipt.stage: receipt for receipt in manifest.stages}
        if len(manifest.stages) != 3 or set(receipts) != {
            "lexical",
            "dense_exact",
            "dense_hnsw",
        }:
            raise IndexGenerationIntegrityError(
                "index generation does not contain all required stages"
            )
        expected_names = {
            "lexical": LEXICAL_NAME,
            "dense_exact": EXACT_NAME,
            "dense_hnsw": HNSW_NAME,
        }
        expected_backends = {
            "lexical": "sqlite-fts5",
            "dense_exact": "faiss-flat-ip",
            "dense_hnsw": "faiss-hnsw",
        }
        for stage, file_name in expected_names.items():
            receipt = receipts[stage]
            if (
                receipt.file_name != file_name
                or receipt.backend != expected_backends[stage]
            ):
                raise IndexGenerationIntegrityError(
                    "index generation segment descriptor is unsupported"
                )
            try:
                file_sha256 = _sha256_file(root / file_name)
            except OSError as error:
                raise IndexGenerationIntegrityError(
                    f"index generation {stage} segment is unavailable"
                ) from error
            if file_sha256 != receipt.file_sha256:
                raise IndexGenerationIntegrityError(
                    f"index generation {stage} segment hash mismatch"
                )
        lexical = SQLiteLexicalIndex(root / LEXICAL_NAME)
        try:
            exact = FaissExactIndex(root / EXACT_NAME)
            try:
                hnsw = FaissHnswIndex(root / HNSW_NAME)
            except BaseException:
                exact.close()
                raise
        except BaseException:
            lexical.close()
            raise
        backend_manifests: dict[str, _SegmentManifest] = {
            "lexical": lexical.manifest,
            "dense_exact": exact.manifest,
            "dense_hnsw": hnsw.manifest,
        }
        try:
            for stage, backend_manifest in backend_manifests.items():
                receipt = receipts[stage]
                if (
                    backend_manifest.generation_id
                    != receipt.segment_generation_id
                    or backend_manifest.chunk_set_sha256 != receipt.chunk_set_sha256
                    or receipt.chunk_set_sha256 != manifest.chunk_set_sha256
                ):
                    raise IndexGenerationIntegrityError(
                        f"index generation {stage} receipt does not match its segment"
                    )
            if (
                exact.manifest.model_lock_artifact_id
                != manifest.model_lock_artifact_id
                or hnsw.manifest.model_lock_artifact_id
                != manifest.model_lock_artifact_id
            ):
                raise IndexGenerationIntegrityError(
                    "dense segments do not match the generation model lock"
                )
            counts = {
                lexical.manifest.chunk_count,
                exact.manifest.vector_count,
                hnsw.manifest.vector_count,
                manifest.statistics.chunk_count,
                *(receipt.item_count for receipt in manifest.stages),
            }
            dimensions = {
                exact.manifest.dimension,
                hnsw.manifest.dimension,
                manifest.statistics.dimension,
            }
            if len(counts) != 1 or len(dimensions) != 1:
                raise IndexGenerationIntegrityError(
                    "index generation chunk count does not match its segments"
                )
            if hnsw.manifest.parameters != manifest.hnsw_parameters:
                raise IndexGenerationIntegrityError(
                    "HNSW segment does not match generation parameters"
                )
        except BaseException:
            hnsw.close()
            exact.close()
            lexical.close()
            raise
        return cls(root, manifest, lexical, exact, hnsw)

    @classmethod
    def build(
        cls,
        path: str | Path,
        chunks: Iterable[AdmittedIndexChunk],
        *,
        snapshot_artifact_id: str,
        model_lock_artifact_id: str,
        limits: IndexBuildLimits,
        hnsw_parameters: HnswParameters | None = None,
        lineage: IndexGenerationLineage | None = None,
    ) -> IndexGeneration:
        """Build and atomically publish all segments from one admitted stream."""

        if not snapshot_artifact_id or not model_lock_artifact_id:
            raise ValueError("index generation input identities must not be empty")
        destination = Path(path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        admitted, statistics = _admit_chunks(chunks, limits)
        lexical_chunks = tuple(
            LexicalIndexChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                ordinal=chunk.ordinal,
                text=chunk.text,
                metadata=chunk.metadata,
            )
            for chunk in admitted
        )
        lexical_limits = LexicalIndexLimits(
            max_chunks=limits.max_chunks,
            max_text_bytes=limits.max_text_bytes,
            max_metadata_bytes=limits.max_metadata_bytes,
        )
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.name}.lexical.",
            dir=destination.parent,
        ) as work:
            lexical_path = Path(work) / LEXICAL_NAME
            try:
                build_lexical_index_segment(
                    lexical_path,
                    lexical_chunks,
                    limits=lexical_limits,
                )
            except BaseException as error:
                raise IndexGenerationBuildError("lexical", (), error) from error
            return cls._build_from_lexical(
                destination,
                lexical_path,
                admitted,
                statistics,
                snapshot_artifact_id=snapshot_artifact_id,
                model_lock_artifact_id=model_lock_artifact_id,
                limits=limits,
                hnsw_parameters=hnsw_parameters,
                lineage=lineage,
            )

    @classmethod
    def build_from_lexical(
        cls,
        path: str | Path,
        lexical_segment_path: str | Path,
        chunks: Iterable[AdmittedIndexChunk],
        *,
        snapshot_artifact_id: str,
        model_lock_artifact_id: str,
        limits: IndexBuildLimits,
        hnsw_parameters: HnswParameters | None = None,
        lineage: IndexGenerationLineage | None = None,
    ) -> IndexGeneration:
        """Build dense segments around one independently completed lexical segment."""

        if not snapshot_artifact_id or not model_lock_artifact_id:
            raise ValueError("index generation input identities must not be empty")
        destination = Path(path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(destination)
        admitted, statistics = _admit_chunks(chunks, limits)
        return cls._build_from_lexical(
            destination,
            Path(lexical_segment_path).resolve(),
            admitted,
            statistics,
            snapshot_artifact_id=snapshot_artifact_id,
            model_lock_artifact_id=model_lock_artifact_id,
            limits=limits,
            hnsw_parameters=hnsw_parameters,
            lineage=lineage,
        )

    @classmethod
    def _build_from_lexical(
        cls,
        destination: Path,
        lexical_segment_path: Path,
        admitted: tuple[AdmittedIndexChunk, ...],
        statistics: IndexBuildStatistics,
        *,
        snapshot_artifact_id: str,
        model_lock_artifact_id: str,
        limits: IndexBuildLimits,
        hnsw_parameters: HnswParameters | None,
        lineage: IndexGenerationLineage | None,
    ) -> IndexGeneration:
        parameters = hnsw_parameters or HnswParameters()
        expected_lexical_chunks = tuple(
            LexicalChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                ordinal=chunk.ordinal,
                text=chunk.text,
                metadata=chunk.metadata,
            )
            for chunk in admitted
        )
        with SQLiteLexicalIndex(lexical_segment_path) as source_lexical:
            if source_lexical.chunks() != expected_lexical_chunks:
                raise ValueError(
                    "lexical segment does not match the admitted dense chunk set"
                )
        dense_records = tuple(
            DenseVectorRecord(
                chunk_id=chunk.chunk_id,
                vector=chunk.vector,
                metadata=chunk.metadata,
            )
            for chunk in admitted
        )
        temporary = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.",
                suffix=".building",
                dir=destination.parent,
            )
        )
        receipts: list[IndexBuildStageReceipt] = []
        stage = "lexical"
        published = False
        try:
            shutil.copyfile(lexical_segment_path, temporary / LEXICAL_NAME)
            with (temporary / LEXICAL_NAME).open("rb") as handle:
                os.fsync(handle.fileno())
            with SQLiteLexicalIndex(temporary / LEXICAL_NAME) as lexical:
                if lexical.chunks() != expected_lexical_chunks:
                    raise ValueError("copied lexical segment content changed")
                receipts.append(
                    _stage_receipt(
                        stage,
                        "sqlite-fts5",
                        temporary / LEXICAL_NAME,
                        lexical.manifest.generation_id,
                        lexical.manifest.chunk_set_sha256,
                        lexical.manifest.chunk_count,
                    )
                )
            stage = "dense_exact"
            with FaissExactIndex.build(
                temporary / EXACT_NAME,
                dense_records,
                model_lock_artifact_id=model_lock_artifact_id,
            ) as exact:
                receipts.append(
                    _stage_receipt(
                        stage,
                        "faiss-flat-ip",
                        temporary / EXACT_NAME,
                        exact.manifest.generation_id,
                        exact.manifest.chunk_set_sha256,
                        exact.manifest.vector_count,
                    )
                )
            stage = "dense_hnsw"
            with FaissHnswIndex.build(
                temporary / HNSW_NAME,
                dense_records,
                model_lock_artifact_id=model_lock_artifact_id,
                parameters=parameters,
            ) as hnsw:
                receipts.append(
                    _stage_receipt(
                        stage,
                        "faiss-hnsw",
                        temporary / HNSW_NAME,
                        hnsw.manifest.generation_id,
                        hnsw.manifest.chunk_set_sha256,
                        hnsw.manifest.vector_count,
                    )
                )
            chunk_set_hashes = {receipt.chunk_set_sha256 for receipt in receipts}
            if len(chunk_set_hashes) != 1:
                raise ValueError("index segments admitted different chunk sets")
            chunk_set_sha256 = chunk_set_hashes.pop()
            initial = IndexGenerationManifest(
                schema_version=SCHEMA_VERSION,
                generation_id="",
                snapshot_artifact_id=snapshot_artifact_id,
                model_lock_artifact_id=model_lock_artifact_id,
                limits=limits,
                statistics=statistics,
                hnsw_parameters=parameters,
                chunk_set_sha256=chunk_set_sha256,
                stages=tuple(receipts),
                lineage=lineage,
            )
            payload = _manifest_payload(initial)
            manifest = IndexGenerationManifest(
                schema_version=initial.schema_version,
                generation_id=_generation_id(payload),
                snapshot_artifact_id=initial.snapshot_artifact_id,
                model_lock_artifact_id=initial.model_lock_artifact_id,
                limits=initial.limits,
                statistics=initial.statistics,
                hnsw_parameters=initial.hnsw_parameters,
                chunk_set_sha256=initial.chunk_set_sha256,
                stages=initial.stages,
                lineage=initial.lineage,
            )
            manifest_path = temporary / MANIFEST_NAME
            manifest_path.write_text(
                _canonical_json(_manifest_payload(manifest)) + "\n",
                encoding="utf-8",
            )
            for child in temporary.iterdir():
                with child.open("rb") as handle:
                    os.fsync(handle.fileno())
            directory_descriptor = os.open(temporary, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
            os.rename(temporary, destination)
            published = True
            parent_descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(parent_descriptor)
            finally:
                os.close(parent_descriptor)
        except BaseException as error:
            shutil.rmtree(temporary, ignore_errors=True)
            if published:
                shutil.rmtree(destination, ignore_errors=True)
            if isinstance(error, IndexGenerationBuildError):
                raise
            raise IndexGenerationBuildError(stage, receipts, error) from error
        return cls.open(destination)

    def admitted_chunks(self) -> tuple[AdmittedIndexChunk, ...]:
        """Return the exact verified material needed to derive a new generation."""

        lexical = {chunk.chunk_id: chunk for chunk in self.lexical.chunks()}
        dense = {record.chunk_id: record for record in self.exact.records()}
        if set(lexical) != set(dense):
            raise ValueError("index generation segment mappings diverged")
        result = []
        for chunk_id in sorted(lexical):
            lexical_chunk = lexical[chunk_id]
            dense_record = dense[chunk_id]
            if lexical_chunk.metadata != dense_record.metadata:
                raise ValueError("index generation segment metadata diverged")
            result.append(
                AdmittedIndexChunk(
                    chunk_id=chunk_id,
                    document_id=lexical_chunk.document_id,
                    ordinal=lexical_chunk.ordinal,
                    text=lexical_chunk.text,
                    vector=dense_record.vector,
                    metadata=lexical_chunk.metadata,
                )
            )
        return tuple(result)

    def close(self) -> None:
        """Close every segment connection."""

        self.hnsw.close()
        self.exact.close()
        self.lexical.close()

    def __enter__(self) -> IndexGeneration:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _stage_receipt(
    stage: str,
    backend: str,
    path: Path,
    generation_id: str,
    chunk_set_sha256: str,
    item_count: int,
) -> IndexBuildStageReceipt:
    return IndexBuildStageReceipt(
        stage=stage,
        backend=backend,
        file_name=path.name,
        file_sha256=_sha256_file(path),
        segment_generation_id=generation_id,
        chunk_set_sha256=chunk_set_sha256,
        item_count=item_count,
    )


__all__ = [
    "AdmittedIndexChunk",
    "IndexBuildLimits",
    "IndexBuildStageReceipt",
    "IndexBuildStatistics",
    "IndexGeneration",
    "IndexGenerationBuildError",
    "IndexGenerationIntegrityError",
    "IndexGenerationLineage",
    "IndexGenerationManifest",
    "LexicalIndexChunk",
    "LexicalIndexLimits",
    "build_lexical_index_segment",
]
