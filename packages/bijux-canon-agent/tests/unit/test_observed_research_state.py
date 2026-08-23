"""Invariant tests for content-addressed observed research transitions."""

from __future__ import annotations

import pytest

from bijux_canon_agent.application import (
    InstalledEvidenceRelation,
    InstalledResearchRequirement,
    ObservedEvidenceRelationKind,
    ObservedResearchDecision,
    ObservedResearchGapKind,
    ObservedResearchStateMachine,
)

_CLAIM = "sha256:" + "1" * 64
_EVIDENCE = "sha256:" + "2" * 64
_UNKNOWN = "sha256:" + "f" * 64


def _initial(*, limit: int = 1, satisfied: bool = True):
    requirement = InstalledResearchRequirement.create(
        description="Establish the finding from direct content.",
        claim_artifact_id=_CLAIM,
        satisfied=satisfied,
    )
    relation = InstalledEvidenceRelation.create(
        claim_artifact_id=_CLAIM,
        evidence_artifact_id=_EVIDENCE,
        kind=ObservedEvidenceRelationKind.SUPPORT,
        material=True,
    )
    return ObservedResearchStateMachine.initial(
        question="What finding does this content establish?",
        requirements=(requirement,),
        claim_artifact_ids=(_CLAIM,),
        evidence_relations=(relation,),
        search_budget_limit=limit,
    )


def test_state_identity_is_deterministic_and_input_dependent() -> None:
    first = _initial()
    repeated = _initial()
    changed = ObservedResearchStateMachine.initial(
        question="What limitation does this content establish?",
        requirements=(
            InstalledResearchRequirement.create(
                description="Establish the finding from direct content.",
                claim_artifact_id=_CLAIM,
                satisfied=True,
            ),
        ),
        claim_artifact_ids=(_CLAIM,),
        evidence_relations=first.evidence_relations,
        search_budget_limit=1,
    )

    assert first.artifact_id == repeated.artifact_id
    assert first.artifact_id != changed.artifact_id


def test_unsatisfied_requirements_are_blocking_observed_gaps() -> None:
    state = _initial(satisfied=False)

    assert tuple(gap.kind for gap in state.blocking_gaps) == (
        ObservedResearchGapKind.UNSATISFIED_REQUIREMENT,
    )


def test_transition_rejects_a_decision_without_an_observed_cause() -> None:
    state = _initial()
    decision = ObservedResearchDecision.create(
        role="researcher",
        operation="search_counterevidence",
        rationale="execute a bounded evidence search",
        cause_artifact_ids=(_UNKNOWN,),
    )

    with pytest.raises(ValueError, match="not caused by the observed state"):
        ObservedResearchStateMachine.transition(state, decision)


@pytest.mark.parametrize("search_budget_limit", [0, 1, 2, 7])
def test_search_consumption_never_exceeds_its_declared_bound(
    search_budget_limit: int,
) -> None:
    state = _initial(limit=search_budget_limit)
    machine = ObservedResearchStateMachine()
    for sequence in range(search_budget_limit):
        decision = ObservedResearchDecision.create(
            role="researcher",
            operation=f"bounded_search_{sequence}",
            rationale="consume one declared search unit",
            cause_artifact_ids=(state.artifact_id,),
        )
        state = machine.transition(state, decision, consume_search=True)

    assert state.search_budget_used == search_budget_limit
    overflow = ObservedResearchDecision.create(
        role="researcher",
        operation="overflow_search",
        rationale="attempt one search beyond the bound",
        cause_artifact_ids=(state.artifact_id,),
    )
    with pytest.raises(ValueError, match="exceeds the search budget"):
        machine.transition(state, overflow, consume_search=True)


def test_terminal_state_rejects_further_decisions() -> None:
    state = _initial()
    finish = ObservedResearchDecision.create(
        role="verifier",
        operation="verify_completed_research",
        rationale="all requirements are satisfied",
        cause_artifact_ids=(state.artifact_id,),
    )
    terminal = ObservedResearchStateMachine.transition(
        state,
        finish,
        terminal_status="completed",
    )
    retry = ObservedResearchDecision.create(
        role="researcher",
        operation="search_after_completion",
        rationale="attempt an illegal post-terminal search",
        cause_artifact_ids=(terminal.artifact_id,),
    )

    with pytest.raises(ValueError, match="terminal observed research state"):
        ObservedResearchStateMachine.transition(terminal, retry)
