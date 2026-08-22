# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Bounded skeptical-search workflow tests."""

from __future__ import annotations

import pytest

from bijux_canon_reason.research import (
    CounterevidenceError,
    CounterevidenceErrorCode,
    CounterevidenceOmissionReason,
    CounterevidencePolicy,
    CounterevidenceSearchOutcome,
    CounterevidenceSearchRun,
    CounterevidenceSearchService,
    CounterevidenceTarget,
    RetrievalBatchStatus,
    RetrievalEvidenceBatch,
    ScopedRetrievalRequest,
    create_counterevidence_target,
    create_retrieval_evidence_batch,
)


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _target(
    claim: str,
    *,
    importance: int = 90,
    graph: str | None = None,
    statement: str = "The intervention improves the measured outcome.",
    known: tuple[str, ...] = (),
) -> CounterevidenceTarget:
    return create_counterevidence_target(
        graph_artifact_id=graph or _artifact("a"),
        claim_artifact_id=_artifact(claim),
        scope_artifact_id=_artifact("b"),
        statement=statement,
        importance=importance,
        known_evidence_artifact_ids=known,
    )


class _Port:
    def __init__(
        self,
        evidence: tuple[str, ...] = (),
        status: RetrievalBatchStatus = RetrievalBatchStatus.no_matches,
        refusal_code: str | None = None,
    ) -> None:
        self.evidence = evidence
        self.status = status
        self.refusal_code = refusal_code
        self.requests: list[ScopedRetrievalRequest] = []

    def retrieve(self, request: ScopedRetrievalRequest) -> RetrievalEvidenceBatch:
        self.requests.append(request)
        return create_retrieval_evidence_batch(
            request,
            retrieval_trace_artifact_id=_artifact("c"),
            generation_artifact_id=_artifact("d"),
            status=self.status,
            evidence_artifact_ids=self.evidence,
            refusal_code=self.refusal_code,
        )


def test_plan_prioritizes_important_claims_and_retains_bounded_omissions() -> None:
    service = CounterevidenceSearchService(
        CounterevidencePolicy(minimum_claim_importance=60, max_claims=1)
    )
    high = _target("1", importance=95)
    deferred = _target("2", importance=80)
    low = _target("3", importance=20)

    plan = service.plan((low, deferred, high))

    assert tuple(item.target_artifact_id for item in plan.requests) == (
        high.claim_artifact_id,
    )
    assert tuple(item.reason for item in plan.omissions) == (
        CounterevidenceOmissionReason.claim_budget,
        CounterevidenceOmissionReason.below_importance,
    )
    assert "contradictory evidence" in plan.requests[0].query_text
    assert "failed replication" in plan.requests[0].query_text
    assert plan.requests[0].prior_evidence_artifact_ids == ()

    run = service.search(plan, _Port())
    assert run.confirmation_only_stop_blocked
    assert run.unsearched_important_claim_artifact_ids == (deferred.claim_artifact_id,)


def test_negative_search_is_bounded_and_never_becomes_support() -> None:
    service = CounterevidenceSearchService()
    plan = service.plan((_target("1"),))

    result = service.search(plan, _Port())
    restarted = CounterevidenceSearchRun.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert not result.confirmation_only_stop_blocked
    assert result.records[0].outcome is (
        CounterevidenceSearchOutcome.no_new_counterevidence_found
    )
    assert result.records[0].candidate_evidence_artifact_ids == ()
    assert result.records[0].negative_search_statement is not None
    assert "absence is not support" in result.records[0].negative_search_statement


def test_new_candidates_require_relation_classification_before_stopping() -> None:
    service = CounterevidenceSearchService()
    plan = service.plan((_target("1"),))

    result = service.search(
        plan,
        _Port(
            (_artifact("e"),),
            status=RetrievalBatchStatus.success,
        ),
    )

    assert result.confirmation_only_stop_blocked
    assert result.records[0].outcome is (
        CounterevidenceSearchOutcome.candidate_evidence_found
    )
    assert result.records[0].requires_relation_classification
    assert result.records[0].candidate_evidence_artifact_ids == (_artifact("e"),)


def test_repeated_known_evidence_is_not_reported_as_new_counterevidence() -> None:
    known = _artifact("e")
    service = CounterevidenceSearchService()
    plan = service.plan((_target("1", known=(known,)),))

    result = service.search(
        plan,
        _Port((known,), status=RetrievalBatchStatus.success),
    )

    assert not result.confirmation_only_stop_blocked
    assert result.records[0].outcome is (
        CounterevidenceSearchOutcome.no_new_counterevidence_found
    )
    assert result.records[0].candidate_evidence_artifact_ids == ()


def test_refused_search_blocks_confirmation_only_stopping() -> None:
    service = CounterevidenceSearchService()
    plan = service.plan((_target("1"),))

    result = service.search(
        plan,
        _Port(
            status=RetrievalBatchStatus.refused,
            refusal_code="scope_denied",
        ),
    )

    assert result.confirmation_only_stop_blocked
    assert result.records[0].outcome is (CounterevidenceSearchOutcome.retrieval_refused)
    assert result.records[0].negative_search_statement is None


def test_invalid_target_sets_and_query_bounds_fail_closed() -> None:
    target = _target("1")
    service = CounterevidenceSearchService()
    with pytest.raises(CounterevidenceError) as duplicate:
        service.plan((target, target))
    assert duplicate.value.code is CounterevidenceErrorCode.duplicate_claim

    with pytest.raises(CounterevidenceError) as mixed:
        service.plan((target, _target("2", graph=_artifact("f"))))
    assert mixed.value.code is CounterevidenceErrorCode.mixed_graph_identity

    bounded = CounterevidenceSearchService(
        CounterevidencePolicy(max_query_characters=64)
    )
    with pytest.raises(CounterevidenceError) as long_query:
        bounded.plan((_target("1", statement="claim " * 30),))
    assert long_query.value.code is CounterevidenceErrorCode.query_budget_exceeded

    empty = service.plan((_target("1", importance=1),))
    with pytest.raises(CounterevidenceError) as no_searches:
        service.search(empty, _Port())
    assert no_searches.value.code is CounterevidenceErrorCode.plan_has_no_searches
