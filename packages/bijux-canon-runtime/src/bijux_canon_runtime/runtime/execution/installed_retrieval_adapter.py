# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed citation-ready retrieval at the Runtime DAG boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from enum import Enum
import hashlib
from pathlib import Path

from bijux_canon_index.application import (
    CitationLocatorCatalog,
    CitationLocatorRecord,
    CitationLocatorSegment,
    CitationLocatorService,
    CitationRetrievalMode,
    CitationSourceMetadata,
    DenseCandidateMode,
    DenseCandidateOutcome,
    DenseCandidateService,
    ExactSourceLocator,
    FusionChannelRanking,
    HybridRetrievalPolicy,
    IndexService,
    LEGACY_RETRIEVAL_POLICY_ID,
    LexicalCandidateService,
    RerankFailurePolicy,
    RerankPolicy,
    VexArtifactStore,
    citation_candidates_from_lexical,
    citation_candidates_from_rerank,
    reciprocal_rank_fusion,
    rerank_candidates,
    resolve_hybrid_retrieval_policy,
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


def _content_id(value: object) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def _is_artifact_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _embedding_cache_observation(embedding: object) -> dict[str, object] | None:
    observer = getattr(embedding, "cache_observation", None)
    if not callable(observer):
        return None
    value = observer()
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise StepDispatchError("embedding cache observation is invalid")
    return value


def _required_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError
    return value


def _required_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError
    return value


def _exact_locator(value: object) -> ExactSourceLocator:
    raw = _required_object(value)
    scheme = raw.get("scheme")
    selectors = raw.get("selectors")
    if (
        not isinstance(scheme, str)
        or not scheme
        or not isinstance(selectors, dict)
        or not selectors
        or any(
            not isinstance(name, str)
            or not name
            or isinstance(item, bool)
            or not isinstance(item, str | int)
            for name, item in selectors.items()
        )
    ):
        raise TypeError
    return ExactSourceLocator(scheme, tuple(sorted(selectors.items())))


def _lineage_segments(
    *,
    raw_record: Mapping[str, object],
    chunk_id: str,
    document_id: str,
    source_sha256: str,
    parser_manifest_sha256: str,
    chunk_text: str,
    mapping_ids: tuple[str, ...],
    section_paths: tuple[tuple[str, ...], ...],
) -> tuple[CitationLocatorSegment, ...]:
    raw_segments = raw_record.get("segments")
    if (
        not isinstance(raw_segments, list)
        or len(raw_segments) != len(mapping_ids)
        or len(section_paths) != len(mapping_ids)
    ):
        raise TypeError
    result: list[CitationLocatorSegment] = []
    for ordinal, (raw_value, mapping_id) in enumerate(
        zip(raw_segments, mapping_ids, strict=True)
    ):
        raw = _required_object(raw_value)
        chunk_span = _required_object(raw.get("chunk_character_span"))
        normalized_span = _required_object(raw.get("normalized_character_span"))
        start = _required_integer(chunk_span.get("start"))
        end = _required_integer(chunk_span.get("end"))
        normalized_start = _required_integer(normalized_span.get("start"))
        normalized_end = _required_integer(normalized_span.get("end"))
        if (
            raw.get("schema_version")
            != "bijux.canon.ingest.citation_lineage_segment.v1"
            or raw.get("chunk_id") != chunk_id
            or raw.get("document_id") != document_id
            or raw.get("source_content_sha256") != source_sha256
            or raw.get("mapping_sha256") != mapping_id
            or chunk_span.get("coordinate_system") != "unicode_code_point"
            or normalized_span.get("coordinate_system") != "unicode_code_point"
            or start < 0
            or end <= start
            or end > len(chunk_text)
        ):
            raise ValueError
        exact_text = chunk_text[start:end]
        exact_text_sha256 = hashlib.sha256(exact_text.encode()).hexdigest()
        locator = _exact_locator(raw.get("locator"))
        locator_sha256 = _content_id(
            {"scheme": locator.scheme, "selectors": dict(locator.selectors)}
        )
        source_document_edge = _content_id(
            {
                "document_id": document_id,
                "parser_manifest_sha256": parser_manifest_sha256,
                "source_content_sha256": source_sha256,
            }
        )
        document_mapping_edge = _content_id(
            {
                "document_id": document_id,
                "locator_sha256": locator_sha256,
                "mapping_sha256": mapping_id,
                "parser_manifest_sha256": parser_manifest_sha256,
            }
        )
        mapping_chunk_edge = _content_id(
            {
                "chunk_character_span": {"end": end, "start": start},
                "chunk_id": chunk_id,
                "mapping_sha256": mapping_id,
                "normalized_text_sha256": exact_text_sha256,
            }
        )
        source_span = _required_object(raw.get("source_span"))
        source_span_start = _required_integer(source_span.get("start"))
        source_span_end = _required_integer(source_span.get("end"))
        if (
            raw.get("normalized_text_sha256") != exact_text_sha256
            or raw.get("parser_manifest_sha256") != parser_manifest_sha256
            or raw.get("locator_sha256") != locator_sha256
            or raw.get("source_document_edge_sha256") != source_document_edge
            or raw.get("document_mapping_edge_sha256") != document_mapping_edge
            or raw.get("mapping_chunk_edge_sha256") != mapping_chunk_edge
            or source_span.get("coordinate_system") != "byte"
            or source_span.get("selected_bytes_sha256") != source_sha256
            or source_span_start < 0
            or source_span_end <= source_span_start
        ):
            raise ValueError
        payload = dict(raw)
        segment_id = payload.pop("segment_sha256", None)
        if segment_id != _content_id(payload):
            raise ValueError
        result.append(
            CitationLocatorSegment(
                ordinal=ordinal,
                mapping_id=mapping_id,
                chunk_start=start,
                chunk_end=end,
                normalized_start=normalized_start,
                normalized_end=normalized_end,
                section_path=section_paths[ordinal],
                locator=locator,
                verbatim_text=exact_text,
                content_sha256=exact_text_sha256,
            )
        )
    return tuple(result)


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
            lineage = raw_document.get("citation_lineage")
            if (
                not isinstance(document_id, str)
                or not isinstance(metadata, dict)
                or not isinstance(chunks, list)
                or not isinstance(lineage, dict)
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
            raw_lineage_records = lineage.get("records")
            if (
                lineage.get("schema_version")
                != "bijux.canon.ingest.document_citation_lineage.v1"
                or lineage.get("document_id") != document_id
                or lineage.get("source_content_sha256") != source_sha256
                or not isinstance(raw_lineage_records, list)
                or not _is_artifact_id(lineage.get("parser_manifest_sha256"))
            ):
                raise TypeError
            parser_manifest_sha256 = str(lineage["parser_manifest_sha256"])
            lineage_payload = dict(lineage)
            lineage_id = lineage_payload.pop("lineage_sha256", None)
            if lineage_id != _content_id(lineage_payload):
                raise ValueError
            lineage_by_chunk: dict[str, dict[str, object]] = {}
            for raw_lineage_record in raw_lineage_records:
                record = _required_object(raw_lineage_record)
                lineage_chunk_id = record.get("chunk_id")
                if (
                    not isinstance(lineage_chunk_id, str)
                    or lineage_chunk_id in lineage_by_chunk
                ):
                    raise ValueError
                record_payload = dict(record)
                record_id = record_payload.pop("record_sha256", None)
                if record_id != _content_id(record_payload):
                    raise ValueError
                lineage_by_chunk[lineage_chunk_id] = record
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
                raw_chunk_id = raw_chunk["chunk_id"]
                raw_chunk_index = raw_chunk["chunk_index"]
                raw_chunk_text = raw_chunk["normalized_text"]
                raw_chunk_text_sha256 = raw_chunk["normalized_text_sha256"]
                if (
                    not _is_artifact_id(raw_chunk_id)
                    or isinstance(raw_chunk_index, bool)
                    or not isinstance(raw_chunk_index, int)
                    or raw_chunk_index < 0
                    or not isinstance(raw_chunk_text, str)
                    or not raw_chunk_text
                    or not isinstance(raw_chunk_text_sha256, str)
                    or hashlib.sha256(raw_chunk_text.encode()).hexdigest()
                    != raw_chunk_text_sha256
                    or any(not _is_artifact_id(item) for item in mapping_ids)
                ):
                    raise ValueError
                chunk_id = raw_chunk_id
                chunk_index = raw_chunk_index
                chunk_text = raw_chunk_text
                chunk_text_sha256 = raw_chunk_text_sha256
                raw_lineage_record = lineage_by_chunk.get(chunk_id)
                if (
                    raw_lineage_record is None
                    or raw_lineage_record.get("schema_version")
                    != "bijux.canon.ingest.citation_lineage_record.v1"
                    or raw_lineage_record.get("document_id") != document_id
                    or raw_lineage_record.get("chunk_index") != chunk_index
                    or raw_lineage_record.get("normalized_text_sha256")
                    != chunk_text_sha256
                ):
                    raise ValueError
                raw_section_paths = raw_lineage_record.get("section_paths")
                if not isinstance(raw_section_paths, list) or len(
                    raw_section_paths
                ) != len(mapping_ids):
                    raise TypeError
                segment_section_paths: list[tuple[str, ...]] = []
                for raw_path in raw_section_paths:
                    if not isinstance(raw_path, list) or any(
                        not isinstance(item, str) or not item for item in raw_path
                    ):
                        raise TypeError
                    segment_section_paths.append(
                        tuple(raw_path) if raw_path else section_path
                    )
                locator_segments = _lineage_segments(
                    raw_record=raw_lineage_record,
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source_sha256=source_sha256,
                    parser_manifest_sha256=parser_manifest_sha256,
                    chunk_text=chunk_text,
                    mapping_ids=tuple(mapping_ids),
                    section_paths=tuple(segment_section_paths),
                )
                records.append(
                    CitationLocatorRecord(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        ordinal=chunk_index,
                        source=source,
                        section_path=section_path,
                        locator=locator_segments[0].locator,
                        verbatim_text=chunk_text,
                        content_sha256=chunk_text_sha256,
                        mapping_ids=tuple(mapping_ids),
                        locator_segments=locator_segments,
                    )
                )
            if set(lineage_by_chunk) != {
                str(raw_chunk["chunk_id"])
                for raw_chunk in chunks
                if isinstance(raw_chunk, dict) and "chunk_id" in raw_chunk
            }:
                raise ValueError
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
        policy: HybridRetrievalPolicy | None = None,
    ) -> None:
        self._store = store
        self._index = index
        self._embedding = embedding
        self._vex_store_root = vex_store_root
        self._policy = policy or resolve_hybrid_retrieval_policy(
            LEGACY_RETRIEVAL_POLICY_ID
        )
        resource_cache = index.resource_cache
        self._lexical = LexicalCandidateService(
            index.registry_root,
            resource_cache=resource_cache,
        )
        self._dense = DenseCandidateService(
            index.registry_root,
            embedder=embedding,
            artifact_store_root=vex_store_root,
            resource_cache=resource_cache,
        )
        self._locators = CitationLocatorService(
            index.registry_root,
            resource_cache=resource_cache,
        )

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
        prepared = self._index.prepare_archive(index_artifact.canonical_bytes)
        inspection = prepared.inspection
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
        hybrid = step.inputs.execution_profile is not ExecutionProfile.OFFLINE_LEXICAL
        candidate_limit = (
            self._policy.candidate_limit(top_k)
            if hybrid
            else min(1000, max(top_k, top_k * 4))
        )
        metadata_filter = _retrieval_filter(step)
        lexical = self._lexical.generate(
            query,
            generation_id=inspection.generation_id,
            top_k=(self._policy.lexical_limit(top_k) if hybrid else top_k),
            candidate_limit=candidate_limit,
            metadata_filter=metadata_filter,
        )
        dense = None
        dense_attempts: list[dict[str, object]] = []
        fusion = None
        rerank = None
        vex_record = None
        fallback_action = "none"
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
            dense = self._dense.generate(
                query,
                generation_id=inspection.generation_id,
                mode=dense_mode,
                top_k=top_k,
                candidate_limit=candidate_limit,
                budget=self._policy.vex_budget(
                    max_latency_ms=step.inputs.budget.timeout_seconds * 1000.0,
                    max_candidates=candidate_limit,
                ),
                metadata_filter=metadata_filter,
                inspection=inspection,
            )
            dense_attempts.append(asdict(dense))
            if (
                dense.outcome is DenseCandidateOutcome.refused
                and dense_mode is DenseCandidateMode.ann
                and self._policy.fallback_to_exact_on_ann_refusal
                and len(dense_attempts) < self._policy.maximum_dense_attempts
            ):
                dense_mode = DenseCandidateMode.exact
                fallback_action = "bounded-exact-after-ann-refusal"
                dense = self._dense.generate(
                    query,
                    generation_id=inspection.generation_id,
                    mode=dense_mode,
                    top_k=candidate_limit,
                    candidate_limit=candidate_limit,
                    budget=self._policy.vex_budget(
                        max_latency_ms=step.inputs.budget.timeout_seconds * 1000.0,
                        max_candidates=candidate_limit,
                    ),
                    metadata_filter=metadata_filter,
                    inspection=inspection,
                )
                dense_attempts.append(asdict(dense))
            if dense.outcome is DenseCandidateOutcome.refused:
                raise StepDispatchError("dense VEX policy refused retrieval evidence")
            fusion = reciprocal_rank_fusion(
                (
                    FusionChannelRanking.from_lexical(lexical),
                    FusionChannelRanking.from_dense(dense),
                ),
                policy=self._policy.fusion_policy(top_k=top_k),
            )
            rerank = rerank_candidates(
                fusion,
                policy=RerankPolicy(
                    enabled=False,
                    candidate_limit=candidate_limit,
                    top_k=top_k,
                    timeout_ms=max(
                        1,
                        int(step.inputs.budget.timeout_seconds * 1000.0),
                    ),
                    failure_policy=RerankFailurePolicy.retain_retrieval_order,
                ),
            )
            candidates = citation_candidates_from_rerank(
                rerank,
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
        resolution = self._locators.resolve(
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
                    "requested_retrieval_mode": step.inputs.execution_profile.value,
                    "retrieval": {
                        "dense": None if dense is None else asdict(dense),
                        "dense_attempts": dense_attempts,
                        "fallback_action": fallback_action,
                        "fusion": None if fusion is None else asdict(fusion),
                        "lexical": asdict(lexical),
                        "policy": self._policy.record(top_k=top_k),
                        "rerank": None if rerank is None else asdict(rerank),
                    },
                    "resource_reuse": {
                        "archive_content_sha256": prepared.archive_content_sha256,
                        "archive_preparation_ms": prepared.preparation_ms,
                        "archive_status": prepared.cache_status.value,
                        "embedding": _embedding_cache_observation(self._embedding),
                        "generation": asdict(self._index.resource_cache.report()),
                        "schema_version": "bijux.canon.index.resource_reuse.v1",
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
