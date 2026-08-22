# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed citation-ready retrieval at the Runtime DAG boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from bijux_canon_index.application import (
    CitationLocatorCatalog,
    CitationLocatorRecord,
    CitationLocatorService,
    CitationRetrievalMode,
    CitationSourceMetadata,
    DenseCandidateMode,
    DenseCandidateOutcome,
    DenseCandidateService,
    ExactSourceLocator,
    FusionChannelRanking,
    IndexService,
    LexicalCandidateService,
    RrfFusionPolicy,
    VexArtifactStore,
    VexExecutionBudget,
    citation_candidates_from_fusion,
    citation_candidates_from_lexical,
    reciprocal_rank_fusion,
)
from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    MetadataOperator,
    UserMetadataPredicate,
)
from bijux_canon_runtime.model.artifact import AddressedArtifact, canonical_json_bytes
from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
    ExecutionProfile,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.installed_operation_adapters import (
    CanonicalEmbeddingService,
    _artifact_input,
    _bounded_output,
    _json_object,
    _validated_snapshot,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _retrieval_filter(step: ConcreteDagStep) -> MetadataFilter | None:
    filters = step.inputs.filters
    if filters is None or not (filters.document_ids or filters.source_uris):
        return None
    user = (
        ()
        if not filters.source_uris
        else (
            UserMetadataPredicate(
                "source_uri",
                MetadataOperator.one_of,
                filters.source_uris,
            ),
        )
    )
    return MetadataFilter(source_ids=filters.document_ids, user=user)


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _first_section_path(value: object, fallback: str) -> tuple[str, ...]:
    if isinstance(value, list):
        for candidate in value:
            if (
                isinstance(candidate, list)
                and candidate
                and all(isinstance(item, str) and item for item in candidate)
            ):
                return tuple(candidate)
    return (fallback,)


def _citation_catalog(
    snapshot_artifact: AddressedArtifact,
    snapshot: Mapping[str, object],
) -> CitationLocatorCatalog:
    raw_documents = snapshot.get("documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise StepDispatchError("corpus snapshot citation records are unavailable")
    records: list[CitationLocatorRecord] = []
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
            relative_path = metadata["relative_path"]
            source_sha256 = metadata["source_content_sha256"]
            format_id = metadata["format_id"]
            if not all(
                isinstance(value, str) and value
                for value in (relative_path, source_sha256, format_id)
            ):
                raise TypeError
            source_uri = metadata.get("canonical_uri")
            if not isinstance(source_uri, str) or not source_uri:
                source_uri = f"urn:bijux:source:{source_sha256}"
            raw_authors = metadata.get("authors", [])
            if not isinstance(raw_authors, list) or not all(
                isinstance(item, str) and item for item in raw_authors
            ):
                raise TypeError
            title = metadata.get("title")
            if not isinstance(title, str) or not title:
                title = relative_path
            source = CitationSourceMetadata(
                source_id=document_id,
                source_uri=source_uri,
                source_content_sha256=source_sha256,
                format_id=format_id,
                title=title,
                authors=tuple(raw_authors),
                doi=_optional_string(metadata.get("doi")),
                language=_optional_string(metadata.get("language")),
                license_id=_optional_string(metadata.get("license_expression")),
            )
            for raw_chunk in chunks:
                if not isinstance(raw_chunk, dict):
                    raise TypeError
                section_path = _first_section_path(
                    raw_chunk.get("section_paths"), relative_path
                )
                mapping_ids = raw_chunk["mapping_sha256"]
                if not isinstance(mapping_ids, list) or not all(
                    isinstance(item, str) and item for item in mapping_ids
                ):
                    raise TypeError
                records.append(
                    CitationLocatorRecord(
                        chunk_id=str(raw_chunk["chunk_id"]),
                        document_id=document_id,
                        ordinal=int(raw_chunk["chunk_index"]),
                        source=source,
                        section_path=section_path,
                        locator=ExactSourceLocator(
                            "bijux-ingest-mapping-set",
                            (("window_ordinal", int(raw_chunk["chunk_index"])),),
                        ),
                        verbatim_text=str(raw_chunk["normalized_text"]),
                        content_sha256=str(raw_chunk["normalized_text_sha256"]),
                        mapping_ids=tuple(mapping_ids),
                    )
                )
    except (KeyError, TypeError, ValueError) as error:
        raise StepDispatchError(
            "corpus snapshot citation records are invalid"
        ) from error
    return CitationLocatorCatalog(
        "bijux.canon.ingest.citation_locator_catalog.v1",
        str(snapshot_artifact.descriptor.artifact_id),
        tuple(records),
    )


class CanonicalRetrievalOperationAdapter:
    """Retrieve citation-ready lexical and VEX evidence from one generation."""

    adapter_id = "bijux-canon-index:citation-ready-retrieval:v1"
    adapter_version = "1.0"
    operation = DagOperation.RETRIEVE

    def __init__(
        self,
        *,
        store: ArtifactPayloadStore,
        index: IndexService,
        embedding: CanonicalEmbeddingService,
        vex_store_root: Path,
    ) -> None:
        self._store = store
        self._index = index
        self._embedding = embedding
        self._vex_store_root = vex_store_root

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        context.raise_if_stopped()
        if step.inputs.query is None or step.inputs.top_k is None:
            raise StepDispatchError("retrieval requires a query and result bound")
        if step.inputs.execution_profile is ExecutionProfile.QDRANT_HYBRID:
            raise StepDispatchError(
                "qdrant retrieval requires separately admitted service authority"
            )
        index_artifact = _artifact_input(
            store=self._store,
            upstream=upstream_artifacts,
            contract_id="index.composite.v1",
            fallback_id=step.inputs.index_id,
        )
        inspection = self._index.admit_archive(
            index_artifact.canonical_bytes,
            activate=True,
        )
        try:
            snapshot_artifact = self._store.load(
                ArtifactID(inspection.snapshot_artifact_id)
            )
        except (KeyError, ValueError) as error:
            raise StepDispatchError(
                "index snapshot lineage is unavailable in Runtime CAS"
            ) from error
        snapshot = _validated_snapshot(
            _json_object(snapshot_artifact, "ingest.corpus-snapshot.v1")
        )
        catalog = _citation_catalog(snapshot_artifact, snapshot)
        query = step.inputs.query
        top_k = step.inputs.top_k
        candidate_limit = min(1000, max(top_k, top_k * 4))
        metadata_filter = _retrieval_filter(step)
        lexical = LexicalCandidateService(self._index.registry_root).generate(
            query,
            generation_id=inspection.generation_id,
            top_k=top_k,
            candidate_limit=candidate_limit,
            metadata_filter=metadata_filter,
        )
        dense = None
        fusion = None
        vex_record = None
        if step.inputs.execution_profile is ExecutionProfile.OFFLINE_LEXICAL:
            retrieval_mode = CitationRetrievalMode.lexical
            candidates = citation_candidates_from_lexical(lexical)
        else:
            dense_mode = (
                DenseCandidateMode.exact
                if step.inputs.execution_profile is ExecutionProfile.LOCAL_HYBRID_EXACT
                else DenseCandidateMode.ann
            )
            self._vex_store_root.mkdir(parents=True, exist_ok=True)
            dense = DenseCandidateService(
                self._index.registry_root,
                embedder=self._embedding,
                artifact_store_root=self._vex_store_root,
            ).generate(
                query,
                generation_id=inspection.generation_id,
                mode=dense_mode,
                top_k=top_k,
                candidate_limit=candidate_limit,
                budget=VexExecutionBudget(
                    max_latency_ms=step.inputs.budget.timeout_seconds * 1000.0,
                    max_memory_bytes=512 * 1024 * 1024,
                    max_candidates=candidate_limit,
                    max_ef_search=10_000,
                    minimum_recall=0.9,
                    require_witness=True,
                ),
                metadata_filter=metadata_filter,
            )
            if dense.outcome is DenseCandidateOutcome.refused:
                raise StepDispatchError("dense VEX policy refused retrieval evidence")
            fusion = reciprocal_rank_fusion(
                (
                    FusionChannelRanking.from_lexical(lexical),
                    FusionChannelRanking.from_dense(dense),
                ),
                policy=RrfFusionPolicy(top_k=top_k),
            )
            candidates = citation_candidates_from_fusion(
                fusion,
                dense_mode=dense_mode,
            )
            retrieval_mode = (
                CitationRetrievalMode.local_hybrid_exact
                if dense_mode is DenseCandidateMode.exact
                else CitationRetrievalMode.local_hybrid_ann
            )
            vex_record = (
                VexArtifactStore(self._vex_store_root).load(dense.artifact_id).record
            )
        resolution = CitationLocatorService(self._index.registry_root).resolve(
            candidates,
            generation_id=inspection.generation_id,
            query_text_sha256=lexical.query_text_sha256,
            retrieval_mode=retrieval_mode,
            catalog=catalog,
        )
        payload = canonical_json_bytes(
            _json_value(
                {
                    "content_trust": "untrusted-source-text",
                    "filters": {
                        "document_ids": list(
                            ()
                            if step.inputs.filters is None
                            else step.inputs.filters.document_ids
                        ),
                        "source_uris": list(
                            ()
                            if step.inputs.filters is None
                            else step.inputs.filters.source_uris
                        ),
                    },
                    "generation_id": inspection.generation_id,
                    "hits": [asdict(hit) for hit in resolution.hits],
                    "index_artifact_id": str(index_artifact.descriptor.artifact_id),
                    "locator_catalog_id": resolution.locator_catalog_id,
                    "query_text_sha256": lexical.query_text_sha256,
                    "retrieval": {
                        "dense": None if dense is None else asdict(dense),
                        "fusion": None if fusion is None else asdict(fusion),
                        "lexical": asdict(lexical),
                    },
                    "retrieval_mode": retrieval_mode.value,
                    "schema_version": "bijux.canon.index.evidence_set.v1",
                    "snapshot_artifact_id": inspection.snapshot_artifact_id,
                    "status": "success" if resolution.hits else "insufficient",
                    "vex_execution": vex_record,
                }
            )
        )
        context.raise_if_stopped()
        return _bounded_output(
            step=step,
            contract_id="index.evidence-set.v1",
            media_type="application/json",
            payload=payload,
            upstream=upstream_artifacts,
            external_dependencies=(
                () if upstream_artifacts else (index_artifact.descriptor.artifact_id,)
            ),
        )


__all__ = ["CanonicalRetrievalOperationAdapter"]
