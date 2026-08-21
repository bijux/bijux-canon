# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from time import sleep

import pytest

from bijux_canon_index.application import (
    FusedCandidate,
    RerankFailurePolicy,
    RerankOutcome,
    RerankPolicy,
    RerankResponse,
    RerankScore,
    RrfFusionBatch,
    rerank_candidates,
)


def _fusion() -> RrfFusionBatch:
    hits = tuple(
        FusedCandidate(
            artifact_id=f"sha256:{rank:064x}",
            rank=rank,
            fused_score=1.0 / rank,
            chunk_id=f"chunk-{rank}",
            document_id=f"doc-{rank}",
            ordinal=0,
            source_text_sha256=f"{rank:064x}",
            contributions=(),
        )
        for rank in range(1, 6)
    )
    return RrfFusionBatch("v1", "generation", "a" * 64, "b" * 64, "c" * 64, hits)


class _Reranker:
    artifact_id = "sha256:" + "d" * 64
    provider = "local-test"
    model_id = "stable-score-v1"

    def __init__(self, *, delay: float = 0, error: Exception | None = None) -> None:
        self.delay = delay
        self.error = error

    def rerank(self, query_text_sha256, candidates):
        sleep(self.delay)
        if self.error:
            raise self.error
        return RerankResponse(
            tuple(RerankScore(hit.chunk_id, float(hit.rank)) for hit in candidates),
            "request-1",
            (("candidates", len(candidates)),),
        )


def _policy(
    *,
    enabled: bool = True,
    failure: RerankFailurePolicy = RerankFailurePolicy.retain_retrieval_order,
    timeout_ms: int = 100,
) -> RerankPolicy:
    return RerankPolicy(enabled, 4, 2, timeout_ms, failure)


def test_reranker_reorders_only_bounded_retrieval_candidates_with_provenance() -> None:
    batch = rerank_candidates(_fusion(), policy=_policy(), reranker=_Reranker())

    assert batch.outcome is RerankOutcome.applied
    assert [candidate.chunk_id for candidate in batch.candidates] == [
        "chunk-4",
        "chunk-3",
    ]
    assert [candidate.retrieval_rank for candidate in batch.candidates] == [4, 3]
    assert batch.provider_request_id == "request-1"
    assert batch.usage == (("candidates", 4),)
    assert all(candidate.chunk_id != "chunk-5" for candidate in batch.candidates)


def test_disabled_reranker_preserves_retrieval_truth_without_provider() -> None:
    batch = rerank_candidates(_fusion(), policy=_policy(enabled=False))

    assert batch.outcome is RerankOutcome.disabled
    assert [candidate.chunk_id for candidate in batch.candidates] == [
        "chunk-1",
        "chunk-2",
    ]
    assert all(candidate.rerank_score is None for candidate in batch.candidates)


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("sensitive-token-123"), ValueError("sensitive-token-123")],
)
def test_reranker_failure_retains_order_without_logging_error_text(failure) -> None:
    batch = rerank_candidates(
        _fusion(),
        policy=_policy(),
        reranker=_Reranker(error=failure),
    )

    assert batch.outcome is RerankOutcome.fallback
    assert [candidate.retrieval_rank for candidate in batch.candidates] == [1, 2]
    assert batch.failure_kind == type(failure).__name__
    assert str(failure) not in repr(batch)


def test_reranker_timeout_returns_with_declared_fallback_or_refusal() -> None:
    fallback = rerank_candidates(
        _fusion(),
        policy=_policy(timeout_ms=1),
        reranker=_Reranker(delay=0.05),
    )
    refused = rerank_candidates(
        _fusion(),
        policy=_policy(
            timeout_ms=1,
            failure=RerankFailurePolicy.refuse,
        ),
        reranker=_Reranker(delay=0.05),
    )

    assert fallback.outcome is RerankOutcome.fallback
    assert fallback.failure_kind == "timeout"
    assert refused.outcome is RerankOutcome.refused
    assert refused.candidates == ()


def test_reranker_rejects_new_missing_or_duplicate_candidates() -> None:
    class Invalid(_Reranker):
        def rerank(self, query_text_sha256, candidates):
            return RerankResponse((RerankScore("new", 1.0),), None)

    batch = rerank_candidates(_fusion(), policy=_policy(), reranker=Invalid())

    assert batch.outcome is RerankOutcome.fallback
    assert batch.failure_kind == "invalid_candidate_set"


def test_rerank_policy_validates_candidate_timeout_and_provider_bounds() -> None:
    with pytest.raises(ValueError, match="bounds"):
        RerankPolicy(True, 1, 2, 10, RerankFailurePolicy.refuse)
    with pytest.raises(ValueError, match="timeout"):
        RerankPolicy(True, 2, 1, 0, RerankFailurePolicy.refuse)
    with pytest.raises(ValueError, match="injected"):
        rerank_candidates(_fusion(), policy=_policy(), reranker=None)
