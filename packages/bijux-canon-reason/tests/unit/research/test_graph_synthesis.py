# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Verified research graph synthesis tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    CitationIntegrityStatus,
    ConflictRelationship,
    SourceQualityGrade,
    create_claim_conflict,
    create_claim_context,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research import (
    AssumptionInsufficiencyDelta,
    AssumptionStatus,
    ConvergenceService,
    EvidenceRelationAttachment,
    EvidenceRelationKind,
    EvidenceRelationTrace,
    GraphAssumption,
    GraphConfidenceBasis,
    GraphEvidenceRelation,
    GraphInsufficiency,
    GraphSynthesisError,
    GraphSynthesisErrorCode,
    InsufficiencyOutcome,
    RelationClassificationMode,
    ResearchDeficiency,
    ResearchDeficiencyKind,
    ResearchDeficiencyStatus,
    ResearchSynthesisOutcome,
    SynthesisClaimSection,
    SynthesisConfidenceLevel,
    VerifiedGraphSynthesis,
    VerifiedGraphSynthesisService,
    ClaimMergingService,
    create_convergence_observation,
    create_mergeable_claim,
)


def _id(value: str) -> str:
    return content_artifact_id({"test": value})


def _relation(
    claim_id: str,
    evidence_id: str,
    kind: EvidenceRelationKind,
) -> GraphEvidenceRelation:
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.evidence_relation",
        "claim_artifact_id": claim_id,
        "evidence_artifact_id": evidence_id,
        "relation": kind.value,
        "strength": 1.0,
        "rationale": f"deterministic {kind.value} verdict",
    }
    return GraphEvidenceRelation(artifact_id=content_artifact_id(payload), **payload)


def _attachment(
    graph_id: str, relations: tuple[GraphEvidenceRelation, ...]
) -> EvidenceRelationAttachment:
    report_id = _id("verification-report")
    traces = []
    for ordinal, relation in enumerate(relations):
        trace_payload = {
            "relation_artifact_id": relation.artifact_id,
            "assessment_artifact_id": _id(f"assessment-{ordinal}"),
            "claim_citation_link_artifact_id": _id(f"link-{ordinal}"),
            "citation_evidence_artifact_id": relation.evidence_artifact_id,
            "integrity": CitationIntegrityStatus.verified.value,
            "deterministic_policy_artifact_id": _id("verification-policy"),
            "verification_report_artifact_id": report_id,
            "provider_provenance_artifact_id": None,
            "classification_mode": RelationClassificationMode.deterministic_verification.value,
        }
        traces.append(
            EvidenceRelationTrace(
                artifact_id=content_artifact_id(trace_payload), **trace_payload
            )
        )
    payload = {
        "schema_version": "bijux.canon.reason.evidence_relation_attachment.v1",
        "graph_artifact_id": graph_id,
        "verification_report_artifact_id": report_id,
        "relations": tuple(item.model_dump(mode="json") for item in relations),
        "traces": tuple(item.model_dump(mode="json") for item in traces),
        "rejected": (),
    }
    return EvidenceRelationAttachment(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_id,
        verification_report_artifact_id=report_id,
        relations=relations,
        traces=tuple(traces),
        rejected=(),
    )


def _assumption(claim_id: str) -> GraphAssumption:
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.assumption",
        "claim_artifact_id": claim_id,
        "statement": "The reported sampling frame represents the target population.",
        "status": AssumptionStatus.declared.value,
        "impact": "high",
    }
    return GraphAssumption(artifact_id=content_artifact_id(payload), **payload)


def _insufficiency(
    claim_id: str, *, sufficient: bool
) -> GraphInsufficiency:
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.insufficiency",
        "claim_artifact_ids": (claim_id,),
        "outcome": (
            InsufficiencyOutcome.sufficient.value
            if sufficient
            else InsufficiencyOutcome.insufficient.value
        ),
        "minimum_supports": 2,
        "observed_supports": 2 if sufficient else 1,
        "missing_information": () if sufficient else ("one independent replication",),
    }
    return GraphInsufficiency(artifact_id=content_artifact_id(payload), **payload)


def _deficiency(graph_id: str, claim_id: str) -> ResearchDeficiency:
    payload = {
        "schema_version": "bijux.canon.reason.research_deficiency.v1",
        "artifact_type": "bijux.canon.reason.research_deficiency",
        "graph_artifact_id": graph_id,
        "target_claim_artifact_id": claim_id,
        "kind": ResearchDeficiencyKind.source_dependence.value,
        "description": "Only one independent source supports the claim.",
        "required_action": "Verify an independent replication.",
        "source_gap_artifact_id": _id("source-gap"),
        "status": ResearchDeficiencyStatus.open.value,
        "priority": 90,
    }
    return ResearchDeficiency(artifact_id=content_artifact_id(payload), **payload)


def _delta(
    graph_id: str,
    attachment: EvidenceRelationAttachment,
    *,
    assumptions: tuple[GraphAssumption, ...] = (),
    insufficiencies: tuple[GraphInsufficiency, ...] = (),
    deficiencies: tuple[ResearchDeficiency, ...] = (),
) -> AssumptionInsufficiencyDelta:
    payload = {
        "schema_version": "bijux.canon.reason.assumption_insufficiency_delta.v1",
        "graph_artifact_id": graph_id,
        "relation_attachment_artifact_id": attachment.artifact_id,
        "assumptions": tuple(item.model_dump(mode="json") for item in assumptions),
        "insufficiencies": tuple(
            item.model_dump(mode="json") for item in insufficiencies
        ),
        "deficiencies": tuple(
            item.model_dump(mode="json") for item in deficiencies
        ),
    }
    return AssumptionInsufficiencyDelta(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_id,
        relation_attachment_artifact_id=attachment.artifact_id,
        assumptions=assumptions,
        insufficiencies=insufficiencies,
        deficiencies=deficiencies,
    )


def _merge(graph_id: str, *, empty: bool = False):
    if empty:
        return ClaimMergingService().merge(graph_artifact_id=graph_id, claims=())
    claims = tuple(
        create_mergeable_claim(
            claim_artifact_id=_id(f"claim-{ordinal}"),
            semantic_key=f"proposition {ordinal}",
            statement=f"Verified finding {ordinal}.",
            scope_artifact_id=_id("scope"),
            evidence_artifact_ids=(_id(f"merge-evidence-{ordinal}"),),
        )
        for ordinal in (1, 2)
    )
    return ClaimMergingService().merge(graph_artifact_id=graph_id, claims=claims)


def _convergence(graph_id: str, *, outcome: str = "converged"):
    kwargs = {
        "iteration": 1,
        "graph_artifact_id": graph_id,
        "coverage": 1.0,
        "verified_answerable_claims": 2,
        "required_claims": 2,
        "blocking_gap_count": 0,
        "new_evidence_count": 1,
        "marginal_evidence_value": 0.2,
        "cumulative_tool_calls": 2,
        "cumulative_tokens": 100,
        "cumulative_elapsed_ms": 20,
        "explicit_insufficiency": False,
        "cancellation_requested": False,
    }
    if outcome == "continue":
        kwargs.update(
            coverage=0.5,
            verified_answerable_claims=1,
            blocking_gap_count=1,
        )
    elif outcome == "insufficient":
        kwargs.update(
            coverage=0.5,
            verified_answerable_claims=1,
            blocking_gap_count=1,
            explicit_insufficiency=True,
        )
    elif outcome == "cancelled":
        kwargs.update(
            coverage=0.5,
            verified_answerable_claims=1,
            blocking_gap_count=1,
            cancellation_requested=True,
        )
    return ConvergenceService().evaluate((create_convergence_observation(**kwargs),))


def _rich_inputs():
    graph_id = _id("graph")
    merge = _merge(graph_id)
    source_1, source_2 = (
        item.source_claim_artifact_id for item in merge.mappings
    )
    relations = (
        _relation(source_1, _id("evidence-1"), EvidenceRelationKind.supports),
        _relation(source_1, _id("evidence-2"), EvidenceRelationKind.supports),
        _relation(source_2, _id("evidence-3"), EvidenceRelationKind.supports),
        _relation(source_2, _id("evidence-4"), EvidenceRelationKind.opposes),
        _relation(source_2, _id("evidence-5"), EvidenceRelationKind.ambiguous),
    )
    attachment = _attachment(graph_id, relations)
    assumption = _assumption(source_2)
    deficiency = _deficiency(graph_id, source_2)
    delta = _delta(
        graph_id,
        attachment,
        assumptions=(assumption,),
        insufficiencies=(
            _insufficiency(source_1, sufficient=True),
            _insufficiency(source_2, sufficient=False),
        ),
        deficiencies=(deficiency,),
    )
    context = create_claim_context(
        claim_artifact_id=source_2,
        population_scope=("admitted cohort",),
        method_scope=("observational study",),
        temporal_scope=("reported interval",),
        uncertainty=("The effect estimate has a wide interval.",),
        limitations=("The study is not randomized.",),
        source_quality=SourceQualityGrade.moderate,
        source_quality_basis="The source reports methods and uncertainty.",
    )
    conflict = create_claim_conflict(
        relationship=ConflictRelationship.divergent,
        claim_artifact_ids=(
            source_2,
            next(
                item.canonical_claim_artifact_id
                for item in merge.mappings
                if item.source_claim_artifact_id == source_2
            ),
        ),
        summary="The source-scoped findings diverge.",
        scope_note="The study populations differ.",
    )
    return graph_id, merge, attachment, delta, context, conflict


def test_synthesizes_consensus_conflict_context_assumptions_and_gaps() -> None:
    graph_id, merge, attachment, delta, context, conflict = _rich_inputs()

    result = VerifiedGraphSynthesisService().synthesize(
        question=" What does the admitted evidence show? ",
        claim_merge=merge,
        evidence_relations=attachment,
        assumption_insufficiency=delta,
        convergence=_convergence(graph_id, outcome="insufficient"),
        contexts=(context,),
        declared_conflicts=(conflict,),
    )
    restarted = VerifiedGraphSynthesis.model_validate_json(result.model_dump_json())

    assert restarted == result
    assert result.outcome is ResearchSynthesisOutcome.partial
    assert len(result.consensus) == 1
    assert len(result.conflicted_claims) == 1
    assert result.consensus[0].confidence.level is SynthesisConfidenceLevel.high
    assert result.conflicted_claims[0].section is SynthesisClaimSection.conflict
    assert result.conflicted_claims[0].confidence.score == 0.166667
    assert len(result.conflicts) == 2
    assert len(result.limitations) == 4
    assert result.assumptions == delta.assumptions
    assert result.remaining_gaps == delta.deficiencies
    assert all(item.artifact_id in result.answer for item in result.conflicts)
    assert "Consensus:" in result.answer
    assert "Remaining gaps:" in result.answer


def test_clean_terminal_graph_is_answered_with_explicit_scope_limit() -> None:
    graph_id = _id("clean-graph")
    merge = _merge(graph_id)
    source_ids = tuple(item.source_claim_artifact_id for item in merge.mappings)
    relations = tuple(
        _relation(source, _id(f"clean-evidence-{ordinal}"), EvidenceRelationKind.supports)
        for ordinal, source in enumerate(source_ids)
    )
    attachment = _attachment(graph_id, relations)
    delta = _delta(graph_id, attachment)

    result = VerifiedGraphSynthesisService().synthesize(
        question="What is supported?",
        claim_merge=merge,
        evidence_relations=attachment,
        assumption_insufficiency=delta,
        convergence=_convergence(graph_id),
    )

    assert result.outcome is ResearchSynthesisOutcome.answered
    assert len(result.consensus) == 2
    assert not result.conflicts
    assert len(result.limitations) == 1
    assert result.limitations[0].source_artifact_ids == tuple(
        sorted((graph_id, merge.artifact_id))
    )


def test_declared_conflict_without_opposition_has_only_declared_provenance() -> None:
    graph_id = _id("declared-conflict-graph")
    merge = _merge(graph_id)
    source_ids = tuple(item.source_claim_artifact_id for item in merge.mappings)
    relations = tuple(
        _relation(source, _id(f"declared-evidence-{ordinal}"), EvidenceRelationKind.supports)
        for ordinal, source in enumerate(source_ids)
    )
    attachment = _attachment(graph_id, relations)
    delta = _delta(graph_id, attachment)
    declaration = create_claim_conflict(
        relationship=ConflictRelationship.divergent,
        claim_artifact_ids=source_ids,
        summary="The admitted claims diverge.",
        scope_note="Their source scopes differ.",
    )

    result = VerifiedGraphSynthesisService().synthesize(
        question="Where does the evidence diverge?",
        claim_merge=merge,
        evidence_relations=attachment,
        assumption_insufficiency=delta,
        convergence=_convergence(graph_id),
        declared_conflicts=(declaration,),
    )

    assert result.outcome is ResearchSynthesisOutcome.partial
    assert not result.consensus
    assert len(result.conflicted_claims) == 2
    assert len(result.conflicts) == 1
    assert result.conflicts[0].source_artifact_ids == (declaration.artifact_id,)


def test_terminal_graph_without_supported_claims_is_insufficient() -> None:
    graph_id = _id("empty-graph")
    merge = _merge(graph_id, empty=True)
    attachment = _attachment(graph_id, ())
    delta = _delta(graph_id, attachment)

    result = VerifiedGraphSynthesisService().synthesize(
        question="Can this be answered?",
        claim_merge=merge,
        evidence_relations=attachment,
        assumption_insufficiency=delta,
        convergence=_convergence(graph_id, outcome="insufficient"),
    )

    assert result.outcome is ResearchSynthesisOutcome.insufficient
    assert not result.consensus and not result.conflicted_claims
    assert "none admitted" in result.answer


@pytest.mark.parametrize(
    ("terminal", "code"),
    [
        ("continue", GraphSynthesisErrorCode.research_not_terminal),
        ("cancelled", GraphSynthesisErrorCode.research_cancelled),
    ],
)
def test_rejects_nonterminal_and_cancelled_research(terminal: str, code) -> None:
    graph_id = _id(f"{terminal}-graph")
    merge = _merge(graph_id, empty=True)
    attachment = _attachment(graph_id, ())
    delta = _delta(graph_id, attachment)

    with pytest.raises(GraphSynthesisError) as error:
        VerifiedGraphSynthesisService().synthesize(
            question="Can this be answered?",
            claim_merge=merge,
            evidence_relations=attachment,
            assumption_insufficiency=delta,
            convergence=_convergence(graph_id, outcome=terminal),
        )
    assert error.value.code is code


def test_rejects_mixed_graph_and_relation_lineage() -> None:
    graph_id = _id("lineage-graph")
    merge = _merge(graph_id, empty=True)
    attachment = _attachment(graph_id, ())
    wrong_attachment = _attachment(_id("other-graph"), ())
    delta = _delta(graph_id, attachment)
    service = VerifiedGraphSynthesisService()

    with pytest.raises(GraphSynthesisError) as graph_error:
        service.synthesize(
            question="Question",
            claim_merge=merge,
            evidence_relations=wrong_attachment,
            assumption_insufficiency=delta,
            convergence=_convergence(graph_id),
        )
    assert graph_error.value.code is GraphSynthesisErrorCode.graph_identity_mismatch

    alien_delta = _delta(graph_id, wrong_attachment)
    with pytest.raises(GraphSynthesisError) as attachment_error:
        service.synthesize(
            question="Question",
            claim_merge=merge,
            evidence_relations=attachment,
            assumption_insufficiency=alien_delta,
            convergence=_convergence(graph_id),
        )
    assert attachment_error.value.code is (
        GraphSynthesisErrorCode.relation_attachment_mismatch
    )


def test_rejects_unknown_claims_and_duplicate_canonical_context() -> None:
    graph_id, merge, attachment, delta, context, _ = _rich_inputs()
    unknown_relation = _relation(
        _id("unknown-claim"), _id("unknown-evidence"), EvidenceRelationKind.supports
    )
    alien_attachment = _attachment(graph_id, (unknown_relation,))
    alien_delta = _delta(graph_id, alien_attachment)
    service = VerifiedGraphSynthesisService()

    with pytest.raises(GraphSynthesisError) as unknown:
        service.synthesize(
            question="Question",
            claim_merge=merge,
            evidence_relations=alien_attachment,
            assumption_insufficiency=alien_delta,
            convergence=_convergence(graph_id),
        )
    assert unknown.value.code is GraphSynthesisErrorCode.unknown_claim

    canonical_id = next(
        item.canonical_claim_artifact_id
        for item in merge.mappings
        if item.source_claim_artifact_id == context.claim_artifact_id
    )
    duplicate = create_claim_context(
        claim_artifact_id=canonical_id,
        population_scope=("another cohort",),
        method_scope=("another method",),
        temporal_scope=("another interval",),
        uncertainty=("another uncertainty",),
        limitations=("another limitation",),
        source_quality=SourceQualityGrade.unknown,
        source_quality_basis="No quality assessment was admitted.",
    )
    with pytest.raises(GraphSynthesisError) as contexts:
        service.synthesize(
            question="Question",
            claim_merge=merge,
            evidence_relations=attachment,
            assumption_insufficiency=delta,
            convergence=_convergence(graph_id, outcome="insufficient"),
            contexts=(context, duplicate),
        )
    assert contexts.value.code is GraphSynthesisErrorCode.incomplete_context


def test_confidence_rejects_asserted_score_or_level() -> None:
    support = (_id("confidence-evidence"),)
    payload = {
        "support_evidence_artifact_ids": support,
        "opposition_evidence_artifact_ids": (),
        "ambiguous_evidence_artifact_ids": (),
        "declared_conflict_artifact_ids": (),
        "material_assumption_artifact_ids": (),
        "open_deficiency_artifact_ids": (),
        "score": 0.5,
        "level": SynthesisConfidenceLevel.moderate.value,
        "calculation": "support/(support+opposition+ambiguity+declared_conflicts+material_assumptions+open_deficiencies)",
    }

    with pytest.raises(ValidationError, match="confidence must be derived"):
        GraphConfidenceBasis(artifact_id=content_artifact_id(payload), **payload)
