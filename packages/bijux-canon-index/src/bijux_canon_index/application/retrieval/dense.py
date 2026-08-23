# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Locked query embedding and generation-bound dense candidate execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum, StrEnum
import hashlib
from pathlib import Path
import platform
from time import perf_counter
import tracemalloc
from typing import Protocol, cast

from bijux_canon_index.application.index_activation import IndexGenerationRegistry
from bijux_canon_index.application.index_audit import IndexCompatibility
from bijux_canon_index.application.index_inspection import IndexInspectionReport
from bijux_canon_index.application.index_resource_cache import (
    IndexGenerationResourceCache,
)
from bijux_canon_index.application.index_service import (
    IndexQueryChannel,
    IndexQueryHit,
    IndexQueryRequest,
    IndexService,
)
from bijux_canon_index.application.vex import (
    VexArtifactStore,
    VexCandidateRecord,
    VexExecutionArtifact,
    VexExecutionBudget,
    VexExecutionObservation,
    VexPolicyDecision,
    VexPolicyStatus,
    evaluate_vex_budget,
)
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.embeddings.local_model import EmbeddedBatch

from .filters import retrieval_filter_capability


class DenseCandidateMode(StrEnum):
    """Dense backend admitted for canonical retrieval."""

    exact = "dense-exact"
    ann = "dense-ann"


class DenseCandidateOutcome(StrEnum):
    """Typed usability of one persisted dense execution."""

    success = "success"
    no_matches = "no_matches"
    refused = "refused"


class QueryEmbeddingProvider(Protocol):
    """Minimal locked embedding boundary required by dense retrieval."""

    def embed(self, texts: Sequence[str]) -> EmbeddedBatch:
        """Embed ordered query texts under one declared model lock."""


class DenseCandidateCompatibilityError(RuntimeError):
    """The query embedding and selected index generation cannot be combined."""


@dataclass(frozen=True, slots=True)
class DenseCandidate:
    """Citation-ready dense locator retaining its backend rank and score."""

    source_rank: int
    score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str


@dataclass(frozen=True, slots=True)
class DenseCandidateBatch:
    """Persisted VEX result and the candidates admitted for later fusion."""

    schema_version: str
    generation_id: str
    model_lock_artifact_id: str
    query_text_sha256: str
    query_vector_sha256: str
    mode: DenseCandidateMode
    requested_top_k: int
    candidate_limit: int
    outcome: DenseCandidateOutcome
    observed_candidates: tuple[DenseCandidate, ...]
    witness_id: str
    execution_id: str
    artifact_id: str
    decision: VexPolicyDecision

    @property
    def candidates(self) -> tuple[DenseCandidate, ...]:
        """Return candidates only when policy admitted their use."""

        if self.outcome is DenseCandidateOutcome.refused:
            return ()
        return self.observed_candidates


def _json_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _filter_payload(metadata_filter: MetadataFilter | None) -> dict[str, object]:
    if metadata_filter is None:
        return {}
    return cast(dict[str, object], _json_value(asdict(metadata_filter)))


def _recall_at_k(report: Sequence[IndexQueryHit], exact_ids: set[str]) -> float:
    observed_ids = {hit.chunk_id for hit in report}
    if not exact_ids:
        return 1.0 if not observed_ids else 0.0
    return len(observed_ids & exact_ids) / len(exact_ids)


def _maximum_score_delta(
    report: Sequence[IndexQueryHit], exact_scores: Mapping[str, float]
) -> float | None:
    deltas = [
        abs(hit.score - exact_scores[hit.chunk_id])
        for hit in report
        if hit.chunk_id in exact_scores
    ]
    return max(deltas) if deltas else None


class DenseCandidateService:
    """Execute exact or approximate dense retrieval through persisted VEX."""

    def __init__(
        self,
        registry_root: str | Path,
        *,
        embedder: QueryEmbeddingProvider,
        artifact_store_root: str | Path,
        compatibility: IndexCompatibility | None = None,
        resource_cache: IndexGenerationResourceCache | None = None,
    ) -> None:
        self._index = IndexService(
            registry_root,
            compatibility=compatibility,
            resource_cache=resource_cache,
        )
        self._registry = IndexGenerationRegistry(
            registry_root,
            compatibility=compatibility,
            resource_cache=self._index.resource_cache,
        )
        self._embedder = embedder
        self._store = VexArtifactStore(artifact_store_root)

    def generate(
        self,
        query_text: str,
        *,
        generation_id: str,
        mode: DenseCandidateMode,
        top_k: int,
        candidate_limit: int,
        budget: VexExecutionBudget,
        metadata_filter: MetadataFilter | None = None,
        inspection: IndexInspectionReport | None = None,
    ) -> DenseCandidateBatch:
        """Embed and execute one bounded dense query with an exact witness."""

        if not query_text.strip():
            raise ValueError("dense query text must not be empty")
        if not isinstance(mode, DenseCandidateMode):
            raise ValueError("dense candidate mode is unsupported")
        if not 1 <= top_k <= 1000:
            raise ValueError("dense top_k must be between 1 and 1000")
        if not top_k <= candidate_limit <= 1000:
            raise ValueError("dense candidate_limit must be within [top_k,1000]")

        selected_inspection = inspection or self._index.verify(generation_id)
        if selected_inspection.generation_id != generation_id:
            raise DenseCandidateCompatibilityError(
                "prepared inspection does not match selected generation"
            )
        with self._registry.lease(generation_id) as generation:
            manifest = generation.manifest
            hnsw_parameters = manifest.hnsw_parameters
            exact_backend_version = generation.exact.manifest.faiss_version
            hnsw_backend_version = generation.hnsw.manifest.faiss_version

        tracing_started_here = not tracemalloc.is_tracing()
        if tracing_started_here:
            tracemalloc.start()
        else:
            tracemalloc.reset_peak()
        started = perf_counter()
        try:
            embedding_started = perf_counter()
            embedded = self._embedder.embed((query_text,))
            embedding_ms = (perf_counter() - embedding_started) * 1000.0
            if embedded.model_lock_id != selected_inspection.model_lock_artifact_id:
                raise DenseCandidateCompatibilityError(
                    "query embedding model lock does not match index generation"
                )
            if len(embedded.vectors) != 1:
                raise DenseCandidateCompatibilityError(
                    "query embedding provider must return exactly one vector"
                )
            query_vector = embedded.vectors[0]
            if len(query_vector) != selected_inspection.dimension:
                raise DenseCandidateCompatibilityError(
                    "query embedding dimension does not match index generation"
                )

            channel = (
                IndexQueryChannel.dense_exact
                if mode is DenseCandidateMode.exact
                else IndexQueryChannel.dense_hnsw
            )
            request = IndexQueryRequest(
                channel=channel,
                query_vector=query_vector,
                top_k=candidate_limit,
                metadata_filter=metadata_filter,
            )
            search_started = perf_counter()
            report = self._index.query(request, generation_id=generation_id)
            witness = self._index.exact_witness(request, generation_id=generation_id)
            search_ms = (perf_counter() - search_started) * 1000.0
            latency_ms = (perf_counter() - started) * 1000.0
            _, memory_bytes = tracemalloc.get_traced_memory()
        finally:
            if tracing_started_here:
                tracemalloc.stop()

        exact_ids = {candidate.chunk_id for candidate in witness.candidates}
        exact_scores = {
            candidate.chunk_id: candidate.score for candidate in witness.candidates
        }
        recall_at_k = _recall_at_k(report.hits, exact_ids)
        ef_search = 0 if mode is DenseCandidateMode.exact else hnsw_parameters.ef_search
        observation = VexExecutionObservation(
            latency_ms=latency_ms,
            memory_bytes=memory_bytes,
            candidate_count=len(report.hits),
            ef_search=ef_search,
            recall_at_k=recall_at_k,
            result_reachability=1.0,
            witness=witness,
        )
        decision = evaluate_vex_budget(budget, observation)
        backend_version = (
            exact_backend_version
            if mode is DenseCandidateMode.exact
            else hnsw_backend_version
        )
        plan: dict[str, object] = {
            "algorithm": "flat-inner-product"
            if mode is DenseCandidateMode.exact
            else "hnsw",
            "backend": report.channel.value,
            "backend_version": backend_version,
            "hardware_class": {
                "machine": platform.machine(),
                "system": platform.system(),
            },
            "metric": witness.metric,
            "normalization": witness.normalization,
            "software_locks": {
                "faiss": backend_version,
                "python": platform.python_version(),
            },
            "embedding_inference_threads": embedded.inference_threads,
        }
        if mode is DenseCandidateMode.ann:
            plan["hnsw_parameters"] = asdict(hnsw_parameters)
        plan["filter_enforcement"] = asdict(
            retrieval_filter_capability(report.channel.value)
        )
        query_text_sha256 = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        artifact = VexExecutionArtifact(
            request={
                "budget": asdict(budget),
                "candidate_limit": candidate_limit,
                "filter": _filter_payload(metadata_filter),
                "generation_id": report.generation_id,
                "model_lock_artifact_id": (selected_inspection.model_lock_artifact_id),
                "query_text_sha256": query_text_sha256,
                "top_k": top_k,
            },
            normalized_vector_sha256=witness.query_vector_sha256,
            plan=plan,
            candidates=tuple(
                VexCandidateRecord(
                    source=report.channel.value,
                    rank=hit.rank,
                    score=hit.score,
                    chunk_id=hit.chunk_id,
                )
                for hit in report.hits
            ),
            witness=witness,
            metrics={
                "candidate_count": len(report.hits),
                "embedding_latency_ms": embedding_ms,
                "latency_ms": latency_ms,
                "maximum_score_delta": _maximum_score_delta(report.hits, exact_scores),
                "memory_bytes": memory_bytes,
                "memory_measurement": "python-allocator-peak-v1",
                "recall_at_k": recall_at_k,
                "result_reachability": 1.0,
                "search_latency_ms": search_ms,
            },
            decision=decision,
            logs=(
                "generation integrity and compatibility verified",
                "query embedded under generation model lock",
                "exact witness and candidate reachability verified",
                f"policy decision: {decision.status.value}",
            ),
        )
        stored = self._store.put(artifact)
        candidates = tuple(
            DenseCandidate(
                source_rank=hit.rank,
                score=hit.score,
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                ordinal=hit.ordinal,
                source_text_sha256=hit.source_text_sha256,
            )
            for hit in report.hits
        )
        if decision.status is not VexPolicyStatus.admitted:
            outcome = DenseCandidateOutcome.refused
        elif candidates:
            outcome = DenseCandidateOutcome.success
        else:
            outcome = DenseCandidateOutcome.no_matches
        return DenseCandidateBatch(
            schema_version="bijux.canon.retrieval.dense_candidates.v1",
            generation_id=report.generation_id,
            model_lock_artifact_id=selected_inspection.model_lock_artifact_id,
            query_text_sha256=query_text_sha256,
            query_vector_sha256=witness.query_vector_sha256,
            mode=mode,
            requested_top_k=top_k,
            candidate_limit=candidate_limit,
            outcome=outcome,
            observed_candidates=candidates,
            witness_id=witness.witness_id,
            execution_id=artifact.execution_id,
            artifact_id=stored.artifact_id,
            decision=decision,
        )


__all__ = [
    "DenseCandidate",
    "DenseCandidateBatch",
    "DenseCandidateCompatibilityError",
    "DenseCandidateMode",
    "DenseCandidateOutcome",
    "DenseCandidateService",
    "QueryEmbeddingProvider",
]
