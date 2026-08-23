"""Ownership and decision tests for the installed Agent research service."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from bijux_canon_agent.application import (
    InstalledResearchClaim,
    InstalledResearchConvergence,
    InstalledResearchPlan,
    InstalledResearchRequest,
    InstalledResearchSearch,
    InstalledResearchSearchRecord,
    InstalledResearchService,
)

_GRAPH = "sha256:" + "1" * 64
_SCOPE = "sha256:" + "2" * 64
_CLAIM = "sha256:" + "3" * 64
_KNOWN = "sha256:" + "4" * 64
_COUNTER_POLICY = "sha256:" + "5" * 64
_CONVERGENCE_POLICY = "sha256:" + "6" * 64
_PLAN = "sha256:" + "7" * 64
_QUERY = "sha256:" + "8" * 64
_SEARCH = "sha256:" + "9" * 64
_CANDIDATE = "sha256:" + "a" * 64
_RETRIEVAL = "sha256:" + "b" * 64
_CONVERGENCE = "sha256:" + "c" * 64


def _request() -> InstalledResearchRequest:
    return InstalledResearchRequest(
        claim_graph_artifact_id=_GRAPH,
        scope_artifact_id=_SCOPE,
        claims=(
            InstalledResearchClaim(
                artifact_id=_CLAIM,
                statement="The method improves endogenous DNA recovery.",
                importance=100,
                known_evidence_artifact_ids=(_KNOWN,),
            ),
        ),
        verified_claim_count=1,
        counterevidence_policy_artifact_id=_COUNTER_POLICY,
        convergence_policy_artifact_id=_CONVERGENCE_POLICY,
    )


@dataclass
class _Port:
    requests: tuple[str, ...] = (_QUERY,)
    candidates: tuple[str, ...] = (_CANDIDATE,)
    calls: list[str] = field(default_factory=list)

    def plan(self, request: InstalledResearchRequest) -> InstalledResearchPlan:
        assert request == _request()
        self.calls.append("plan")
        return InstalledResearchPlan(_PLAN, self.requests, {"requests": []})

    def search(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
    ) -> InstalledResearchSearch:
        assert request == _request()
        assert plan.artifact_id == _PLAN
        self.calls.append("search")
        return InstalledResearchSearch(
            artifact_id=_SEARCH,
            records=(
                InstalledResearchSearchRecord(
                    claim_artifact_id=_CLAIM,
                    outcome="candidate_evidence_found",
                    candidate_evidence_artifact_ids=self.candidates,
                    negative_search_statement=None,
                    record={"outcome": "candidate_evidence_found"},
                ),
            ),
            unsearched_important_claim_artifact_ids=(),
            retrieval_artifact_ids=(_RETRIEVAL,),
            retrieval_records=({"artifact_id": _RETRIEVAL},),
            record={"records": []},
        )

    def evaluate(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
        search: InstalledResearchSearch | None,
    ) -> InstalledResearchConvergence:
        assert request == _request()
        assert plan.artifact_id == _PLAN
        self.calls.append("evaluate")
        return InstalledResearchConvergence(
            artifact_id=_CONVERGENCE,
            outcome="budget_exhausted",
            stop=True,
            record={"stop": True},
        )


def test_service_owns_search_decision_and_causal_trace() -> None:
    port = _Port()
    result = InstalledResearchService().research(_request(), port)

    assert port.calls == ["plan", "search", "evaluate"]
    assert result.opposition_candidate_ids == (_CANDIDATE,)
    assert result.relation_status == "unclassified"
    assert len(result.causal_events) == 4
    assert [event.role for event in result.causal_events] == [
        "plan",
        "skeptic",
        "analyze",
        "terminate",
    ]
    assert result.causal_events[1].evidence_artifact_ids == (_CANDIDATE,)
    assert result.causal_events[-1].budget_decision_artifact_ids == (_CONVERGENCE,)
    assert result.causal_trace.head_artifact_id == result.causal_events[-1].artifact_id


def test_service_skips_search_when_plan_has_no_requests() -> None:
    port = _Port(requests=())
    result = InstalledResearchService().research(_request(), port)

    assert port.calls == ["plan", "evaluate"]
    assert [event.role for event in result.causal_events] == [
        "plan",
        "analyze",
        "terminate",
    ]
    assert result.search is None
    assert result.relation_status == "no-new-counterevidence"


def test_service_rejects_an_untyped_port_result() -> None:
    port = _Port()
    port.plan = lambda request: {"artifact_id": _PLAN}  # type: ignore[method-assign,assignment]

    with pytest.raises(TypeError, match="invalid plan"):
        InstalledResearchService().research(_request(), port)
