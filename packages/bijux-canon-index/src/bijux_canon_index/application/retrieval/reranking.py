# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Optional bounded reranking that cannot introduce retrieval candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import math
from queue import Empty, Queue
from threading import Thread
from time import perf_counter
from typing import Protocol

from .fusion import FusedCandidate, RrfFusionBatch


class RerankFailurePolicy(StrEnum):
    """Stable behavior when an optional reranker cannot be used."""

    retain_retrieval_order = "retain-retrieval-order"
    refuse = "refuse"


class RerankOutcome(StrEnum):
    """Typed result of optional reranking."""

    disabled = "disabled"
    applied = "applied"
    fallback = "fallback"
    refused = "refused"


@dataclass(frozen=True, slots=True)
class RerankScore:
    """One provider score bound to an existing retrieved chunk."""

    chunk_id: str
    score: float

    def __post_init__(self) -> None:
        if not self.chunk_id or not math.isfinite(self.score):
            raise ValueError("rerank scores require a chunk identity and finite score")


@dataclass(frozen=True, slots=True)
class RerankResponse:
    """Scores and secret-safe usage provenance returned by a reranker."""

    scores: tuple[RerankScore, ...]
    provider_request_id: str | None
    usage: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if self.usage != tuple(sorted(set(self.usage))) or any(
            not key or value < 0 for key, value in self.usage
        ):
            raise ValueError("rerank usage must be unique, ordered, and non-negative")


class Reranker(Protocol):
    """Injected reranker identity and bounded candidate scoring operation."""

    @property
    def artifact_id(self) -> str: ...

    @property
    def provider(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    def rerank(
        self,
        query_text_sha256: str,
        candidates: tuple[FusedCandidate, ...],
    ) -> RerankResponse: ...


@dataclass(frozen=True, slots=True)
class RerankPolicy:
    """Candidate, output, timeout, and failure bounds for reranking."""

    enabled: bool
    candidate_limit: int
    top_k: int
    timeout_ms: int
    failure_policy: RerankFailurePolicy

    def __post_init__(self) -> None:
        if not 1 <= self.top_k <= self.candidate_limit <= 1000:
            raise ValueError(
                "rerank bounds require 1 <= top_k <= candidate_limit <= 1000"
            )
        if self.timeout_ms <= 0:
            raise ValueError("rerank timeout must be positive")
        if not isinstance(self.failure_policy, RerankFailurePolicy):
            raise ValueError("rerank failure policy is unsupported")


@dataclass(frozen=True, slots=True)
class RerankedCandidate:
    """Final rank retaining both retrieval truth and optional provider score."""

    rank: int
    retrieval_rank: int
    chunk_id: str
    fused_score: float
    rerank_score: float | None
    candidate: FusedCandidate


@dataclass(frozen=True, slots=True)
class RerankBatch:
    """Bounded rerank result with provider, timing, and fallback provenance."""

    schema_version: str
    generation_id: str
    query_text_sha256: str
    policy_sha256: str
    outcome: RerankOutcome
    reranker_artifact_id: str | None
    provider: str | None
    model_id: str | None
    provider_request_id: str | None
    usage: tuple[tuple[str, int], ...]
    latency_ms: float
    failure_kind: str | None
    candidates: tuple[RerankedCandidate, ...]
    filter_sha256: str = hashlib.sha256(b"{}").hexdigest()
    authorization_scope_id: str | None = None


def _sha256_json(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _retrieval_order(
    hits: tuple[FusedCandidate, ...],
    top_k: int,
) -> tuple[RerankedCandidate, ...]:
    return tuple(
        RerankedCandidate(
            rank=rank,
            retrieval_rank=hit.rank,
            chunk_id=hit.chunk_id,
            fused_score=hit.fused_score,
            rerank_score=None,
            candidate=hit,
        )
        for rank, hit in enumerate(hits[:top_k], start=1)
    )


def _failure(
    fusion: RrfFusionBatch,
    policy: RerankPolicy,
    reranker: Reranker,
    *,
    latency_ms: float,
    failure_kind: str,
) -> RerankBatch:
    fallback = policy.failure_policy is RerankFailurePolicy.retain_retrieval_order
    return RerankBatch(
        schema_version="bijux.canon.retrieval.rerank.v1",
        generation_id=fusion.generation_id,
        query_text_sha256=fusion.query_text_sha256,
        policy_sha256=_sha256_json(asdict(policy)),
        outcome=RerankOutcome.fallback if fallback else RerankOutcome.refused,
        reranker_artifact_id=reranker.artifact_id,
        provider=reranker.provider,
        model_id=reranker.model_id,
        provider_request_id=None,
        usage=(),
        latency_ms=latency_ms,
        failure_kind=failure_kind,
        candidates=_retrieval_order(fusion.hits, policy.top_k) if fallback else (),
        filter_sha256=fusion.filter_sha256,
        authorization_scope_id=fusion.authorization_scope_id,
    )


def rerank_candidates(
    fusion: RrfFusionBatch,
    *,
    policy: RerankPolicy,
    reranker: Reranker | None = None,
) -> RerankBatch:
    """Rerank a bounded prefix, or apply the declared failure behavior."""

    if not policy.enabled:
        return RerankBatch(
            schema_version="bijux.canon.retrieval.rerank.v1",
            generation_id=fusion.generation_id,
            query_text_sha256=fusion.query_text_sha256,
            policy_sha256=_sha256_json(asdict(policy)),
            outcome=RerankOutcome.disabled,
            reranker_artifact_id=None,
            provider=None,
            model_id=None,
            provider_request_id=None,
            usage=(),
            latency_ms=0.0,
            failure_kind=None,
            candidates=_retrieval_order(fusion.hits, policy.top_k),
            filter_sha256=fusion.filter_sha256,
            authorization_scope_id=fusion.authorization_scope_id,
        )
    if reranker is None:
        raise ValueError("enabled reranking requires an injected reranker")
    pool = fusion.hits[: policy.candidate_limit]
    queue: Queue[tuple[RerankResponse | None, Exception | None]] = Queue(maxsize=1)

    def execute() -> None:
        try:
            queue.put((reranker.rerank(fusion.query_text_sha256, pool), None))
        except Exception as error:
            queue.put((None, error))

    started = perf_counter()
    worker = Thread(target=execute, name="bijux-reranker", daemon=True)
    worker.start()
    try:
        response, error = queue.get(timeout=policy.timeout_ms / 1000.0)
    except Empty:
        latency_ms = (perf_counter() - started) * 1000.0
        return _failure(
            fusion,
            policy,
            reranker,
            latency_ms=latency_ms,
            failure_kind="timeout",
        )
    latency_ms = (perf_counter() - started) * 1000.0
    if error is not None:
        return _failure(
            fusion,
            policy,
            reranker,
            latency_ms=latency_ms,
            failure_kind=type(error).__name__,
        )
    assert response is not None
    expected_ids = {hit.chunk_id for hit in pool}
    score_ids = tuple(score.chunk_id for score in response.scores)
    if len(score_ids) != len(set(score_ids)) or set(score_ids) != expected_ids:
        return _failure(
            fusion,
            policy,
            reranker,
            latency_ms=latency_ms,
            failure_kind="invalid_candidate_set",
        )
    scores = {score.chunk_id: score.score for score in response.scores}
    ordered = sorted(
        pool,
        key=lambda hit: (-scores[hit.chunk_id], hit.rank, hit.chunk_id),
    )
    candidates = tuple(
        RerankedCandidate(
            rank=rank,
            retrieval_rank=hit.rank,
            chunk_id=hit.chunk_id,
            fused_score=hit.fused_score,
            rerank_score=scores[hit.chunk_id],
            candidate=hit,
        )
        for rank, hit in enumerate(ordered[: policy.top_k], start=1)
    )
    return RerankBatch(
        schema_version="bijux.canon.retrieval.rerank.v1",
        generation_id=fusion.generation_id,
        query_text_sha256=fusion.query_text_sha256,
        policy_sha256=_sha256_json(asdict(policy)),
        outcome=RerankOutcome.applied,
        reranker_artifact_id=reranker.artifact_id,
        provider=reranker.provider,
        model_id=reranker.model_id,
        provider_request_id=response.provider_request_id,
        usage=response.usage,
        latency_ms=latency_ms,
        failure_kind=None,
        candidates=candidates,
        filter_sha256=fusion.filter_sha256,
        authorization_scope_id=fusion.authorization_scope_id,
    )


__all__ = [
    "RerankBatch",
    "RerankFailurePolicy",
    "RerankOutcome",
    "RerankPolicy",
    "RerankResponse",
    "RerankScore",
    "RerankedCandidate",
    "Reranker",
    "rerank_candidates",
]
