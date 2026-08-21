# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Expected-value research gap-filling tests."""

from __future__ import annotations

import pytest

from bijux_canon_reason.research import (
    EvidenceChange,
    GapFillingError,
    GapFillingErrorCode,
    GapFillingPolicy,
    GapFillingRun,
    GapFillingService,
    GapFillingSourceKind,
    GapFillingStopReason,
    GapResolutionStatus,
    RetrievalBatchStatus,
    RetrievalEvidenceBatch,
    ScopedRetrievalRequest,
    create_gap_filling_candidate,
    create_retrieval_evidence_batch,
)


def _artifact(value: str) -> str:
    return "sha256:" + value * 64


def _candidate(
    source: str,
    *,
    impact: float = 1.0,
    probability: float = 0.9,
    cost: int = 3,
    graph: str | None = None,
    query: str = "external validation cohort evidence",
    status: GapResolutionStatus = GapResolutionStatus.unresolved,
):
    return create_gap_filling_candidate(
        graph_artifact_id=graph or _artifact("a"),
        source_artifact_id=_artifact(source),
        source_kind=GapFillingSourceKind.research_deficiency,
        target_claim_artifact_id=_artifact("b"),
        scope_artifact_id=_artifact("c"),
        query_text=query,
        rationale="Resolve a material answer gap with independent evidence.",
        answer_impact=impact,
        resolution_probability=probability,
        evidence_cost=cost,
        status=status,
    )


class _Port:
    def __init__(self, evidence: tuple[str, ...]) -> None:
        self.evidence = evidence
        self.requests: list[ScopedRetrievalRequest] = []

    def retrieve(self, request: ScopedRetrievalRequest) -> RetrievalEvidenceBatch:
        self.requests.append(request)
        return create_retrieval_evidence_batch(
            request,
            retrieval_trace_artifact_id=_artifact("d"),
            generation_artifact_id=_artifact("e"),
            status=(
                RetrievalBatchStatus.success
                if self.evidence
                else RetrievalBatchStatus.no_matches
            ),
            evidence_artifact_ids=self.evidence,
        )


def test_ranks_expected_value_and_uses_remaining_cost_budget() -> None:
    service = GapFillingService(
        GapFillingPolicy(
            max_requests=3,
            evidence_cost_budget=6,
            minimum_expected_value=0.05,
        )
    )
    highest = _candidate("1", impact=1.0, probability=0.9, cost=3)
    too_expensive = _candidate("2", impact=0.8, probability=0.9, cost=4)
    affordable = _candidate("3", impact=0.5, probability=0.5, cost=2)
    low_value = _candidate("4", impact=0.2, probability=0.1, cost=2)

    plan = service.plan((low_value, affordable, too_expensive, highest))

    assert tuple(item.source_artifact_id for item in plan.decisions) == (
        highest.source_artifact_id,
        too_expensive.source_artifact_id,
        affordable.source_artifact_id,
        low_value.source_artifact_id,
    )
    assert tuple(item.disposition.value for item in plan.decisions) == (
        "selected",
        "evidence_budget",
        "selected",
        "expected_value_below_threshold",
    )
    assert plan.projected_evidence_cost == 5
    assert plan.stop_reasons == (
        GapFillingStopReason.evidence_budget,
        GapFillingStopReason.expected_value_floor,
    )
    assert tuple(item.top_k for item in plan.requests) == (3, 2)
    assert tuple(item.priority for item in plan.requests) == (100, 99)


def test_request_query_and_resolved_limits_are_explicit() -> None:
    service = GapFillingService(
        GapFillingPolicy(
            max_requests=1,
            evidence_cost_budget=10,
            max_query_characters=20,
            minimum_expected_value=0,
        )
    )
    selected = _candidate("1", impact=1.0, cost=2, query="short query")
    request_limited = _candidate("2", impact=0.8, cost=3, query="other short query")
    query_limited = _candidate("3", impact=1.0, cost=1, query="long query " * 10)
    resolved = _candidate("4", status=GapResolutionStatus.resolved)

    plan = service.plan((resolved, query_limited, request_limited, selected))

    dispositions = {
        item.source_artifact_id: item.disposition.value for item in plan.decisions
    }
    assert dispositions[selected.source_artifact_id] == "selected"
    assert dispositions[request_limited.source_artifact_id] == "request_budget"
    assert dispositions[query_limited.source_artifact_id] == "query_budget"
    assert dispositions[resolved.source_artifact_id] == "already_resolved"
    assert plan.stop_reasons == (
        GapFillingStopReason.query_budget,
        GapFillingStopReason.request_budget,
    )


def test_executes_only_selected_requests_and_preserves_evidence_delta() -> None:
    service = GapFillingService(
        GapFillingPolicy(max_requests=1, evidence_cost_budget=10)
    )
    plan = service.plan((_candidate("1"), _candidate("2")))
    port = _Port((_artifact("f"),))

    result = service.fill(plan, port)
    restarted = GapFillingRun.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert len(port.requests) == 1
    assert result.records[0].change is EvidenceChange.evidence_added
    assert result.records[0].added_evidence_artifact_ids == (_artifact("f"),)
    assert result.stop_reasons == (GapFillingStopReason.request_budget,)


def test_value_floor_closes_without_calling_retrieval() -> None:
    service = GapFillingService(GapFillingPolicy(minimum_expected_value=0.5))
    plan = service.plan((_candidate("1"),))
    port = _Port((_artifact("f"),))

    result = service.fill(plan, port)

    assert not port.requests
    assert result.retrieval_run_artifact_id is None
    assert result.records == ()
    assert result.stop_reasons == (GapFillingStopReason.expected_value_floor,)


def test_duplicate_and_mixed_graph_candidates_fail_closed() -> None:
    service = GapFillingService()
    candidate = _candidate("1")

    with pytest.raises(GapFillingError) as duplicate:
        service.plan((candidate, candidate))
    assert duplicate.value.code is GapFillingErrorCode.duplicate_candidate

    with pytest.raises(GapFillingError) as duplicate_gap:
        service.plan((candidate, _candidate("1", impact=0.5)))
    assert duplicate_gap.value.code is GapFillingErrorCode.duplicate_gap

    with pytest.raises(GapFillingError) as mixed:
        service.plan((candidate, _candidate("2", graph=_artifact("9"))))
    assert mixed.value.code is GapFillingErrorCode.mixed_graph_identity
