"""Ownership and decision tests for the installed Agent research service."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest

from bijux_canon_agent.application import (
    BudgetAction,
    BudgetDimensions,
    InstalledCandidateClassification,
    InstalledEvidenceRelation,
    InstalledResearchClaim,
    InstalledResearchConvergence,
    InstalledResearchPlan,
    InstalledResearchRequest,
    InstalledResearchRequirement,
    InstalledResearchSearch,
    InstalledResearchSearchRecord,
    InstalledResearchService,
    ObservedEvidenceRelationKind,
    ObservedResearchGapKind,
    TargetedSearchPlan,
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
_REQUIREMENT = "sha256:" + "d" * 64
_CLASSIFICATION = "sha256:" + "e" * 64
_DOCUMENT = "sha256:" + "0" * 64


def _request(
    *,
    satisfied: bool = True,
    relation: ObservedEvidenceRelationKind | None = None,
    include_opposition: bool = True,
    max_searches: int = 1,
) -> InstalledResearchRequest:
    requirement = InstalledResearchRequirement.create(
        description="Establish whether the method improves endogenous DNA recovery.",
        claim_artifact_id=_CLAIM,
        satisfied=satisfied,
        query_text=(
            None
            if satisfied
            else "direct evidence for endogenous DNA recovery improvement"
        ),
        evidence_artifact_ids=(_KNOWN,) if satisfied else (),
    )
    opposition = InstalledResearchRequirement.create(
        description="Search for material opposition to the recovery claim.",
        claim_artifact_id=_CLAIM,
        satisfied=False,
        kind="opposition",
        priority=90,
        query_text="contradictory evidence for endogenous DNA recovery improvement",
        source_requirement_artifact_id=_REQUIREMENT,
    )
    evidence_relation = InstalledEvidenceRelation.create(
        claim_artifact_id=_CLAIM,
        evidence_artifact_id=_KNOWN,
        kind=(
            relation
            if relation is not None
            else (
                ObservedEvidenceRelationKind.SUPPORT
                if satisfied
                else ObservedEvidenceRelationKind.INSUFFICIENCY
            )
        ),
        material=True,
    )
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
        verified_claim_count=int(satisfied),
        counterevidence_policy_artifact_id=_COUNTER_POLICY,
        convergence_policy_artifact_id=_CONVERGENCE_POLICY,
        question="Does the method improve endogenous DNA recovery?",
        requirements=(
            (requirement, opposition)
            if satisfied and include_opposition
            else (requirement,)
        ),
        evidence_relations=(evidence_relation,),
        max_searches=max_searches,
        requirement_plan_artifact_id=_PLAN,
        requirement_plan_record={"outcome": "search_required"},
        requirement_plan_outcome="search_required",
        budget_limits=BudgetDimensions(
            iterations=max_searches * 2 + 2,
            retrievals=max_searches,
            documents=max_searches,
            candidates=max_searches,
            evidence_items=max_searches,
            tool_calls=max_searches,
            elapsed_ms=30_000,
            memory_bytes=1_000_000,
            artifact_bytes=1_000_000,
        ),
        maximum_search_candidates=1,
    )


@dataclass
class _Port:
    requests: tuple[str, ...] = (_QUERY,)
    candidates: tuple[str, ...] = (_CANDIDATE,)
    search_outcome: str = "candidate_evidence_found"
    convergence_outcome: str = "budget_exhausted"
    convergence_stop: bool = True
    search_error: Exception | None = None
    search_outcomes: tuple[str, ...] = ()
    candidate_sequences: tuple[tuple[str, ...], ...] = ()
    classification_relation: str | None = None
    classification_material: bool = True
    document_artifact_ids: tuple[str, ...] = (_DOCUMENT,)
    plan_execution_usage: BudgetDimensions = BudgetDimensions()
    search_execution_usage: BudgetDimensions = BudgetDimensions()
    evaluation_execution_usage: BudgetDimensions = BudgetDimensions()
    calls: list[str] = field(default_factory=list)

    def plan(
        self,
        request: InstalledResearchRequest,
        targeted_search_plan: TargetedSearchPlan | None,
    ) -> InstalledResearchPlan:
        assert request.claims[0].artifact_id == _CLAIM
        self.calls.append("plan")
        requests = (
            self.requests
            if targeted_search_plan is not None
            and targeted_search_plan.attempt is not None
            else ()
        )
        return InstalledResearchPlan(
            _PLAN,
            requests,
            {"requests": []},
            targeted_search_plan,
            self.plan_execution_usage,
        )

    def search(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
    ) -> InstalledResearchSearch:
        assert request.claims[0].artifact_id == _CLAIM
        assert plan.artifact_id == _PLAN
        self.calls.append("search")
        if self.search_error is not None:
            raise self.search_error
        search_index = self.calls.count("search") - 1
        outcome = (
            self.search_outcomes[search_index]
            if search_index < len(self.search_outcomes)
            else self.search_outcome
        )
        candidates = (
            self.candidate_sequences[search_index]
            if search_index < len(self.candidate_sequences)
            else self.candidates
        )
        attempt = (
            None
            if plan.targeted_search_plan is None
            else plan.targeted_search_plan.attempt
        )
        classifications = (
            ()
            if self.classification_relation is None
            else tuple(
                InstalledCandidateClassification(
                    artifact_id=_CLASSIFICATION,
                    requirement_artifact_id=(
                        _REQUIREMENT
                        if attempt is None
                        else attempt.requirement_artifact_id
                    ),
                    claim_artifact_id=_CLAIM,
                    evidence_artifact_id=candidate,
                    relation=self.classification_relation,
                    rationale="candidate was classified against the exact claim",
                    method="deterministic_semantic",
                    confidence=0.9,
                    material=self.classification_material,
                    record={"artifact_id": _CLASSIFICATION},
                )
                for candidate in candidates
            )
        )
        return InstalledResearchSearch(
            artifact_id=_SEARCH,
            document_artifact_ids=self.document_artifact_ids,
            records=(
                InstalledResearchSearchRecord(
                    claim_artifact_id=_CLAIM,
                    outcome=outcome,
                    candidate_evidence_artifact_ids=candidates,
                    negative_search_statement=(
                        None
                        if candidates
                        else "No new counterevidence was found within this search."
                    ),
                    record={"outcome": outcome},
                    requirement_artifact_id=(
                        None if attempt is None else attempt.requirement_artifact_id
                    ),
                    target_claim_artifact_ids=(_CLAIM,),
                    attempt_artifact_id=(
                        None if attempt is None else attempt.artifact_id
                    ),
                    classifications=classifications,
                ),
            ),
            unsearched_important_claim_artifact_ids=(),
            retrieval_artifact_ids=(_RETRIEVAL,),
            retrieval_records=({"artifact_id": _RETRIEVAL},),
            record={"records": []},
            execution_usage=self.search_execution_usage,
        )

    def evaluate(
        self,
        request: InstalledResearchRequest,
        plan: InstalledResearchPlan,
        search: InstalledResearchSearch | None,
    ) -> InstalledResearchConvergence:
        assert request.claims[0].artifact_id == _CLAIM
        assert plan.artifact_id == _PLAN
        self.calls.append("evaluate")
        return InstalledResearchConvergence(
            artifact_id=_CONVERGENCE,
            outcome=self.convergence_outcome,
            stop=self.convergence_stop,
            record={"stop": self.convergence_stop},
            execution_usage=self.evaluation_execution_usage,
        )


def test_service_owns_search_decision_and_causal_trace() -> None:
    port = _Port()
    result = InstalledResearchService().research(_request(), port)

    assert port.calls == ["plan", "search", "evaluate"]
    assert result.opposition_candidate_ids == (_CANDIDATE,)
    assert result.relation_status == "unclassified"
    assert len(result.causal_events) == 5
    assert [event.role for event in result.causal_events] == [
        "plan",
        "researcher",
        "skeptic",
        "adjudicator",
        "verifier",
    ]
    assert result.causal_events[2].evidence_artifact_ids == (_CANDIDATE,)
    assert result.causal_events[-1].budget_decision_artifact_ids == tuple(
        item.artifact_id for item in result.budget_decisions[-3:]
    )
    assert result.budget_usage.retrievals == 1
    assert result.budget_usage.documents == 1
    assert any(
        item.action is BudgetAction.RESERVED for item in result.budget_decisions
    )
    assert result.causal_trace.head_artifact_id == result.causal_events[-1].artifact_id
    assert len(result.state_history) == len(result.causal_events) + 1
    for index, event in enumerate(result.causal_events):
        assert event.state_before_artifact_id == result.state_history[index].artifact_id
        assert (
            event.state_after_artifact_id == result.state_history[index + 1].artifact_id
        )
        assert event.operation_artifact_id == (
            result.state_history[index + 1].decisions[-1].artifact_id
        )
    assert result.final_state.terminal_status == "incomplete"
    assert result.final_state.search_budget_used == 1
    assert result.terminal_outcome.kind == "incomplete_budget"
    assert result.terminal_outcome.exhausted_budget_dimensions == ("retrievals",)
    assert result.terminal_outcome.remaining_work.pending
    assert result.terminal_outcome.remaining_work.unresolved_evidence_artifact_ids == (
        _CANDIDATE,
    )
    assert any(
        gap.kind is ObservedResearchGapKind.UNCLASSIFIED_EVIDENCE
        for gap in result.final_state.blocking_gaps
    )


def test_service_skips_search_when_plan_has_no_requests() -> None:
    port = _Port(
        requests=(),
        convergence_outcome="converged",
        convergence_stop=True,
    )
    result = InstalledResearchService().research(
        _request(include_opposition=False), port
    )

    assert port.calls == ["plan", "evaluate"]
    assert [event.role for event in result.causal_events] == [
        "plan",
        "verifier",
        "verifier",
    ]
    assert result.search is None
    assert result.relation_status == "sufficient-evidence"
    assert result.final_state.terminal_status == "completed"
    assert result.final_state.search_budget_used == 0
    assert result.terminal_outcome.kind == "converged"
    assert not result.terminal_outcome.remaining_work.pending


def test_material_opposition_remains_a_blocking_observed_gap() -> None:
    port = _Port(
        candidates=(),
        search_outcome="no_new_counterevidence_found",
        convergence_outcome="converged",
    )
    result = InstalledResearchService().research(
        _request(relation=ObservedEvidenceRelationKind.OPPOSITION),
        port,
    )

    assert result.final_state.terminal_status == "incomplete"
    assert any(
        gap.kind is ObservedResearchGapKind.MATERIAL_OPPOSITION
        for gap in result.final_state.blocking_gaps
    )


def test_semantically_classified_support_resolves_the_searched_requirement() -> None:
    port = _Port(
        classification_relation="supporting",
        convergence_outcome="converged",
    )

    result = InstalledResearchService().research(_request(), port)

    assert result.relation_status == "supporting"
    assert result.final_state.terminal_status == "completed"
    assert all(requirement.satisfied for requirement in result.final_state.requirements)
    assert not result.final_state.blocking_gaps
    assert result.targeted_search_observations[0].outcome == "support"
    assert result.terminal_outcome.kind == "converged"


def test_semantically_classified_opposition_blocks_completion() -> None:
    port = _Port(
        classification_relation="opposing",
        convergence_outcome="insufficient",
    )

    result = InstalledResearchService().research(_request(), port)

    assert result.relation_status == "opposing"
    assert result.final_state.terminal_status == "insufficient"
    assert any(
        gap.kind is ObservedResearchGapKind.MATERIAL_OPPOSITION
        for gap in result.final_state.blocking_gaps
    )
    assert result.targeted_search_observations[0].outcome == "opposition"
    assert result.terminal_outcome.kind == "abstained"
    assert result.terminal_outcome.remaining_work.unresolved_gap_artifact_ids


def test_ambiguous_search_takes_the_adjudication_branch() -> None:
    port = _Port(search_outcome="ambiguous_evidence")
    result = InstalledResearchService().research(_request(), port)

    assert result.relation_status == "ambiguous"
    assert [event.role for event in result.causal_events][2:4] == [
        "skeptic",
        "adjudicator",
    ]
    assert any(
        gap.kind is ObservedResearchGapKind.AMBIGUOUS_EVIDENCE
        for gap in result.final_state.blocking_gaps
    )


def test_no_results_are_retained_without_closing_the_opposition_need() -> None:
    port = _Port(
        candidates=(),
        search_outcome="no_new_counterevidence_found",
        convergence_outcome="converged",
    )
    result = InstalledResearchService().research(_request(), port)

    assert [event.role for event in result.causal_events] == [
        "plan",
        "researcher",
        "verifier",
        "adjudicator",
        "verifier",
    ]
    assert result.final_state.terminal_status == "incomplete"
    no_results = tuple(
        gap
        for gap in result.final_state.gaps
        if gap.kind is ObservedResearchGapKind.NO_RESULTS
    )
    assert len(no_results) == 1
    assert no_results[0].blocking is False


def test_no_results_cause_a_distinct_second_query_before_candidates_stop() -> None:
    port = _Port(
        search_outcomes=(
            "no_new_counterevidence_found",
            "candidate_evidence_found",
        ),
        candidate_sequences=((), (_CANDIDATE,)),
    )

    result = InstalledResearchService().research(_request(max_searches=2), port)

    assert port.calls == ["plan", "search", "plan", "search", "evaluate"]
    assert len(result.plan_history) == 2
    assert len(result.search_history) == 2
    attempts = tuple(
        plan.targeted_search_plan.attempt
        for plan in result.plan_history
        if plan.targeted_search_plan is not None
    )
    assert all(attempt is not None for attempt in attempts)
    assert attempts[0].query_text != attempts[1].query_text  # type: ignore[union-attr]
    assert "alternative terminology" in attempts[1].query_text  # type: ignore[union-attr]
    assert [
        observation.outcome for observation in result.targeted_search_observations
    ] == [
        "no_results",
        "material_candidate",
    ]
    assert result.final_state.search_budget_used == 2
    assert result.final_state.terminal_status == "incomplete"
    assert result.terminal_outcome.kind == "incomplete_budget"
    assert result.terminal_outcome.remaining_work.unsatisfied_requirement_artifact_ids


def test_search_tool_failure_is_an_incomplete_data_dependent_branch() -> None:
    port = _Port(search_error=TimeoutError("secret-bearing provider failure"))
    result = InstalledResearchService().research(_request(), port)

    assert port.calls == ["plan", "search", "evaluate"]
    assert result.search is None
    assert result.relation_status == "tool-failure"
    assert result.tool_failure_artifact_ids
    assert result.final_state.terminal_status == "incomplete"
    assert [event.operation for event in result.causal_events] == [
        "plan_counterevidence",
        "record_search_tool_failure",
        "retain_incomplete_research",
    ]
    assert "secret-bearing" not in str(result.final_state.to_record())
    assert result.terminal_outcome.kind == "failed"
    assert result.terminal_outcome.failure_artifact_ids


def test_installed_search_reservation_denial_executes_no_tool_call() -> None:
    request = _request()
    request = replace(
        request,
        budget_limits=BudgetDimensions(
            **{
                **request.budget_limits.payload(),
                "documents": 0,
            }
        ),
    )
    port = _Port()

    result = InstalledResearchService().research(request, port)

    assert port.calls == ["plan"]
    assert result.search is None
    assert result.budget_usage.retrievals == 0
    assert result.budget_usage.tool_calls == 0
    assert result.budget_usage.documents == 0
    assert result.terminal_outcome.kind == "incomplete_budget"
    assert result.terminal_outcome.exhausted_budget_dimensions == ("documents",)
    assert any(
        event.operation == "refuse_unbudgeted_search"
        for event in result.causal_events
    )


def test_installed_oversized_search_result_is_not_admitted() -> None:
    request = _request()
    port = _Port(
        candidates=(_CANDIDATE, "sha256:" + "f" * 64),
        document_artifact_ids=(_DOCUMENT, "sha256:" + "1" * 64),
    )

    result = InstalledResearchService().research(request, port)

    assert port.calls == ["plan", "search"]
    assert result.search is None
    assert result.search_history == ()
    assert result.opposition_candidate_ids == ()
    assert result.budget_usage.retrievals == 1
    assert result.budget_usage.candidates == 0
    assert result.terminal_outcome.kind == "incomplete_budget"
    assert result.terminal_outcome.exhausted_budget_dimensions == (
        "documents",
        "candidates",
        "evidence_items",
    )
    assert any(
        event.operation == "refuse_oversized_search_result"
        for event in result.causal_events
    )


def test_installed_provider_usage_overrun_is_not_admitted() -> None:
    port = _Port(plan_execution_usage=BudgetDimensions(provider_calls=1))

    result = InstalledResearchService().research(_request(), port)

    assert port.calls == ["plan"]
    assert result.plan.record["outcome"] == "budget_exhausted"
    assert result.budget_usage.provider_calls == 0
    assert result.terminal_outcome.kind == "incomplete_budget"
    assert result.terminal_outcome.exhausted_budget_dimensions == (
        "provider_calls",
    )


def test_unsatisfied_requirement_without_a_search_is_not_completed() -> None:
    port = _Port(
        requests=(),
        convergence_outcome="converged",
    )
    result = InstalledResearchService().research(
        _request(satisfied=False, max_searches=0), port
    )

    assert port.calls == ["plan", "evaluate"]
    assert result.causal_events[1].role == "adjudicator"
    assert result.final_state.terminal_status == "incomplete"


def test_service_rejects_an_untyped_port_result() -> None:
    port = _Port()
    port.plan = lambda request, targeted: {  # type: ignore[method-assign,assignment]
        "artifact_id": _PLAN
    }

    with pytest.raises(TypeError, match="invalid plan"):
        InstalledResearchService().research(_request(), port)
