"""Requirement-specific and adaptive search-planning evidence."""

from __future__ import annotations

from bijux_canon_agent.application import (
    InstalledResearchRequirement,
    TargetedSearchDisposition,
    TargetedSearchIntent,
    TargetedSearchObservation,
    TargetedSearchOutcome,
    TargetedSearchPlanningService,
    TargetedSearchPolicy,
    TargetedSearchTrigger,
    query_equivalence_key,
)


def _id(character: str) -> str:
    return "sha256:" + character * 64


def _requirement(
    character: str,
    *,
    kind: str,
    query: str | None,
    priority: int,
    satisfied: bool = False,
    material: bool = True,
    claim: str | None = None,
    dependencies: tuple[str, ...] = (),
) -> InstalledResearchRequirement:
    return InstalledResearchRequirement.create(
        description=f"Resolve substantive {kind} evidence for the answer.",
        claim_artifact_id=claim,
        satisfied=satisfied,
        kind=kind,
        status="satisfied" if satisfied else "unresolved",
        priority=priority,
        material=material,
        dependency_requirement_artifact_ids=dependencies,
        query_text=query,
        evidence_artifact_ids=(_id("e"),) if satisfied else (),
        source_requirement_artifact_id=_id(character),
    )


def test_different_content_needs_produce_distinct_intents_and_queries() -> None:
    claim = _id("c")
    opposition = _requirement(
        "1",
        kind="opposition",
        query=(
            "Did petrous part C yield up to 65-fold more endogenous DNA than "
            "part B contradictory evidence"
        ),
        priority=90,
        claim=claim,
    )
    limitation = _requirement(
        "2",
        kind="limitation",
        query="petrous bone preservation below one percent hot climates limitations",
        priority=80,
    )
    planner = TargetedSearchPlanningService()

    first = planner.plan((limitation, opposition))
    assert first.attempt is not None
    assert first.attempt.intent is TargetedSearchIntent.OPPOSITION
    assert "65-fold" in first.attempt.query_text
    observation = TargetedSearchObservation.create(
        attempt_artifact_id=first.attempt.artifact_id,
        outcome=TargetedSearchOutcome.SUPPORT,
        evidence_artifact_ids=(_id("f"),),
    )
    second = planner.plan(
        (limitation, opposition),
        attempts=(first.attempt,),
        observations=(observation,),
    )

    assert second.attempt is not None
    assert second.attempt.intent is TargetedSearchIntent.LIMITATION
    assert "hot climates" in second.attempt.query_text
    assert second.attempt.query_text != first.attempt.query_text


def test_no_results_trigger_a_distinct_context_query_within_bound() -> None:
    requirement = _requirement(
        "1",
        kind="finding",
        query="direct evidence petrous part C endogenous DNA recovery",
        priority=95,
        claim=_id("c"),
    )
    planner = TargetedSearchPlanningService(
        TargetedSearchPolicy(max_attempts=3, max_attempts_per_requirement=2)
    )
    first_plan = planner.plan((requirement,))
    first = first_plan.attempt
    assert first is not None
    no_results = TargetedSearchObservation.create(
        attempt_artifact_id=first.artifact_id,
        outcome=TargetedSearchOutcome.NO_RESULTS,
    )

    second_plan = planner.plan(
        (requirement,), attempts=(first,), observations=(no_results,)
    )
    second = second_plan.attempt
    assert second is not None
    assert second.trigger is TargetedSearchTrigger.NO_RESULTS
    assert second.query_text != first.query_text
    assert "alternative terminology" in second.query_text
    assert second.prior_attempt_artifact_ids == (first.artifact_id,)

    exhausted = planner.plan(
        (requirement,),
        attempts=(first, second),
        observations=(
            no_results,
            TargetedSearchObservation.create(
                attempt_artifact_id=second.artifact_id,
                outcome=TargetedSearchOutcome.NO_RESULTS,
            ),
        ),
    )
    assert exhausted.attempt is None
    assert exhausted.decisions[0].disposition is TargetedSearchDisposition.ATTEMPT_BUDGET


def test_ambiguity_and_opposition_select_different_adaptive_queries() -> None:
    requirement = _requirement(
        "1",
        kind="disambiguation",
        query="Corded Ware ancestry exact regional definition",
        priority=98,
        claim=_id("c"),
    )
    planner = TargetedSearchPlanningService()
    first = planner.plan((requirement,)).attempt
    assert first is not None

    ambiguous = planner.plan(
        (requirement,),
        attempts=(first,),
        observations=(
            TargetedSearchObservation.create(
                attempt_artifact_id=first.artifact_id,
                outcome=TargetedSearchOutcome.AMBIGUOUS,
            ),
        ),
    ).attempt
    opposing = planner.plan(
        (requirement,),
        attempts=(first,),
        observations=(
            TargetedSearchObservation.create(
                attempt_artifact_id=first.artifact_id,
                outcome=TargetedSearchOutcome.OPPOSITION,
                evidence_artifact_ids=(_id("f"),),
            ),
        ),
    ).attempt

    assert ambiguous is not None and opposing is not None
    assert ambiguous.trigger is TargetedSearchTrigger.AMBIGUOUS_RESULT
    assert opposing.trigger is TargetedSearchTrigger.OPPOSING_RESULT
    assert "geography time quantity" in ambiguous.query_text
    assert "reconcile disagreement" in opposing.query_text
    assert ambiguous.query_equivalence_sha256 != opposing.query_equivalence_sha256


def test_equivalent_queries_are_not_repeated() -> None:
    first_requirement = _requirement(
        "1",
        kind="finding",
        query="Ancient DNA!",
        priority=95,
        claim=_id("c"),
    )
    equivalent_requirement = _requirement(
        "2",
        kind="finding",
        query="ancient dna",
        priority=94,
        claim=_id("d"),
    )
    planner = TargetedSearchPlanningService()
    first = planner.plan((first_requirement, equivalent_requirement)).attempt
    assert first is not None
    observed = TargetedSearchObservation.create(
        attempt_artifact_id=first.artifact_id,
        outcome=TargetedSearchOutcome.SUPPORT,
        evidence_artifact_ids=(_id("f"),),
    )
    second = planner.plan(
        (first_requirement, equivalent_requirement),
        attempts=(first,),
        observations=(observed,),
    )

    assert query_equivalence_key("Ancient DNA!") == query_equivalence_key(
        "ancient dna"
    )
    assert second.attempt is None
    by_requirement = {
        item.requirement_artifact_id: item for item in second.decisions
    }
    assert (
        by_requirement[equivalent_requirement.artifact_id].disposition
        is TargetedSearchDisposition.EQUIVALENT_QUERY
    )


def test_dependencies_and_materiality_prevent_unjustified_calls() -> None:
    answerability = _requirement(
        "1",
        kind="answerability",
        query="is this in corpus scope",
        priority=100,
    )
    finding = _requirement(
        "2",
        kind="finding",
        query="direct result evidence",
        priority=95,
        claim=_id("c"),
        dependencies=(_id("1"),),
    )
    optional_method = _requirement(
        "3",
        kind="method_context",
        query="sampling method context",
        priority=85,
        material=False,
    )

    plan = TargetedSearchPlanningService().plan(
        (finding, optional_method, answerability)
    )

    assert plan.attempt is not None
    assert plan.attempt.requirement_artifact_id == answerability.artifact_id
    dispositions = {
        item.requirement_artifact_id: item.disposition for item in plan.decisions
    }
    assert dispositions[finding.artifact_id] is TargetedSearchDisposition.DEPENDENCY_UNRESOLVED
    assert dispositions[optional_method.artifact_id] is TargetedSearchDisposition.NON_MATERIAL


def test_material_candidate_and_refusal_pause_adaptive_search() -> None:
    requirement = _requirement(
        "1",
        kind="opposition",
        query="counterevidence for petrous recovery claim",
        priority=90,
        claim=_id("c"),
    )
    planner = TargetedSearchPlanningService()
    attempt = planner.plan((requirement,)).attempt
    assert attempt is not None

    for outcome, evidence in (
        (TargetedSearchOutcome.MATERIAL_CANDIDATE, (_id("f"),)),
        (TargetedSearchOutcome.REFUSED, ()),
    ):
        plan = planner.plan(
            (requirement,),
            attempts=(attempt,),
            observations=(
                TargetedSearchObservation.create(
                    attempt_artifact_id=attempt.artifact_id,
                    outcome=outcome,
                    evidence_artifact_ids=evidence,
                ),
            ),
        )
        assert plan.attempt is None
        assert plan.decisions[0].disposition is TargetedSearchDisposition.CLOSED_BY_OBSERVATION
