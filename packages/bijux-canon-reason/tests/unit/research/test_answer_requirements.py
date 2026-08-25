# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Reviewed question-level answer requirement planning cases."""

from __future__ import annotations

import hashlib

from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    CitationVerificationReport,
    EntailmentVerdict,
    EvidenceEntailmentAssessment,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionDecision,
    GroundingAdmissionService,
    GroundingRequestStatus,
    ImmutableEvidenceLocator,
    LocalGroundedAnswer,
    LocalGroundedAnswerService,
    VerifiedAtomicClaim,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id
from bijux_canon_reason.research.answer_requirements import (
    AnswerRequirementKind,
    AnswerRequirementPlan,
    AnswerRequirementPlanningService,
    AnswerRequirementPlanOutcome,
    AnswerRequirementStatus,
    SkepticalSearchCompletion,
    create_skeptical_search_completion,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _evidence(name: str, text: str, rank: int) -> CitationEvidence:
    return CitationEvidence(
        artifact_id=_artifact(f"evidence:{name}"),
        chunk_artifact_id=_artifact(f"chunk:{name}"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id=f"document-{name}",
        source_id=f"source-{name}",
        section_path=("article", "results"),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact(f"locator:{name}"),
            source_artifact_id=_artifact(f"source:{name}"),
            source_uri=f"https://example.test/{name}",
            source_content_sha256=_sha(f"source-content:{name}"),
            scheme="unicode-code-point",
            selectors=(("char_start", 0), ("char_end", len(text))),
        ),
        exact_text=text,
        exact_text_sha256=_sha(text),
        rank=rank,
        relevance_score=1.0 / rank,
    )


def _source(name: str) -> CitationSourceDescriptor:
    return CitationSourceDescriptor.create(
        source_id=f"source-{name}",
        title=f"Source {name}",
        canonical_uri=f"https://example.test/{name}",
        doi=None,
        source_content_sha256=_sha(f"source-content:{name}"),
    )


def _answer(question: str, *evidence: CitationEvidence) -> LocalGroundedAnswer:
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=800,
            citation_budget=8,
            claim_budget=8,
            max_per_source=4,
            max_per_section=8,
        )
    ).build(
        question_artifact_id=_artifact(f"question:{question}"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=evidence,
    )
    names = tuple(item.source_id.removeprefix("source-") for item in evidence)
    return LocalGroundedAnswerService().answer(
        question=question,
        evidence_packet=packet,
        sources=tuple(_source(name) for name in names),
        max_points=8,
    )


def _plan(
    answer: LocalGroundedAnswer,
    *,
    admission: GroundingAdmissionDecision | None = None,
    verification: CitationVerificationReport | None = None,
    completed: tuple[str, ...] = (),
    completions: tuple[SkepticalSearchCompletion, ...] = (),
) -> AnswerRequirementPlan:
    return AnswerRequirementPlanningService().plan(
        question=answer.synthesis.question,
        graph_artifact_id=_artifact("graph"),
        scope_artifact_id=_artifact("scope"),
        claims=answer.claims,
        verification=verification or answer.verification,
        admission=admission or answer.admission,
        synthesis=answer.synthesis,
        skeptical_search_completions=(
            tuple(
                create_skeptical_search_completion(
                    claim_artifact_id=claim_id,
                    search_run_artifact_id=_artifact(f"search:{claim_id}"),
                )
                for claim_id in completed
            )
            + completions
        ),
    )


def test_sufficient_answer_can_plan_zero_additional_searches() -> None:
    answer = _answer(
        "What DNA yield was reported?",
        _evidence("yield", "Endogenous DNA yield reached 65 percent.", 1),
    )
    claim_ids = tuple(item.artifact_id for item in answer.claims.claims)
    plan = _plan(answer, completed=claim_ids)
    restarted = AnswerRequirementPlan.model_validate_json(plan.model_dump_json())

    assert restarted == plan
    assert plan.outcome is AnswerRequirementPlanOutcome.READY_WITHOUT_SEARCH
    assert plan.search_requirement_artifact_ids == ()
    assert {item.kind for item in plan.requirements} >= {
        AnswerRequirementKind.ANSWERABILITY,
        AnswerRequirementKind.FINDING,
        AnswerRequirementKind.METHOD_CONTEXT,
        AnswerRequirementKind.OPPOSITION,
        AnswerRequirementKind.LIMITATION,
    }
    assert all(
        item.status is AnswerRequirementStatus.SATISFIED for item in plan.requirements
    )


def test_petrous_bone_content_drives_finding_limitation_and_opposition_needs() -> None:
    question = (
        "Which petrous-bone region produced the highest endogenous DNA yield, "
        "and what quantitative advantage and hot-climate caveat were reported?"
    )
    answer = _answer(
        question,
        _evidence(
            "quantitative-result",
            "Our results confirm that dense petrous part C can exceed part B by up to 65-fold and part A by up to 177-fold.",
            1,
        ),
        _evidence(
            "hot-caveat",
            "Our results also show that while yields from part C were lower than 1% in hot regions, damage patterns indicated ancient DNA molecules.",
            2,
        ),
        _evidence(
            "region-definition",
            "We sampled three regions: cortical bone (part A), the otic capsule edge (part B), and the dense part within the otic capsule (part C).",
            3,
        ),
    )
    plan = _plan(answer)
    findings = tuple(
        item for item in plan.requirements if item.kind is AnswerRequirementKind.FINDING
    )
    opposition = tuple(
        item
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.OPPOSITION
    )

    assert any("65-fold" in item.description for item in findings)
    assert any("lower than 1%" in item.description for item in findings)
    assert len(opposition) == len(findings)
    assert all(item.target_claim_artifact_ids for item in opposition)
    assert all(
        item.artifact_id in plan.search_requirement_artifact_ids for item in opposition
    )
    assert any(
        item.kind is AnswerRequirementKind.LIMITATION
        and item.status is AnswerRequirementStatus.SATISFIED
        for item in plan.requirements
    )


def test_conflicting_question_plans_claim_specific_opposition_searches() -> None:
    answer = _answer(
        "What conflict or counterevidence did the two studies report?",
        _evidence("positive", "The first assay detected ancient DNA.", 1),
        _evidence("negative", "The second assay did not detect ancient DNA.", 2),
    )
    plan = _plan(answer)
    opposition = tuple(
        item
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.OPPOSITION
    )

    assert len(opposition) == len(answer.claims.claims)
    assert all(item.status is AnswerRequirementStatus.UNRESOLVED for item in opposition)
    assert all(item.target_claim_artifact_ids for item in opposition)
    assert all("contradictory evidence" in str(item.query_text) for item in opposition)
    assert plan.outcome is AnswerRequirementPlanOutcome.SEARCH_REQUIRED


def test_unclassified_material_candidate_keeps_opposition_unresolved() -> None:
    answer = _answer(
        "What DNA yield was reported?",
        _evidence("yield", "Endogenous DNA yield reached 65 percent.", 1),
    )
    claim_id = answer.claims.claims[0].artifact_id
    candidate_id = _artifact("candidate-opposition")
    completion = create_skeptical_search_completion(
        claim_artifact_id=claim_id,
        search_run_artifact_id=_artifact("skeptical-search"),
        material_candidate_artifact_ids=(candidate_id,),
        classified_candidate_artifact_ids=(),
    )
    plan = _plan(answer, completions=(completion,))
    opposition = next(
        item
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.OPPOSITION
    )

    assert opposition.status is AnswerRequirementStatus.UNRESOLVED
    assert opposition.evidence_artifact_ids == (completion.artifact_id,)
    assert opposition.artifact_id in plan.search_requirement_artifact_ids


def test_ambiguous_claim_creates_a_material_disambiguation_need() -> None:
    answer = _answer(
        "What DNA yield was reported?",
        _evidence("yield", "Endogenous DNA yield reached 65 percent.", 1),
    )
    original_claim = answer.verification.claims[0]
    original_assessment = original_claim.assessments[0]
    assessment_payload = original_assessment.model_dump(
        mode="json", exclude={"artifact_id"}
    )
    assessment_payload["verdict"] = EntailmentVerdict.ambiguity.value
    assessment_payload["rationale_code"] = "reviewed_scope_ambiguity"
    assessment = EvidenceEntailmentAssessment(
        artifact_id=content_artifact_id(assessment_payload),
        **assessment_payload,
    )
    claim_payload = original_claim.model_dump(mode="json", exclude={"artifact_id"})
    claim_payload["verdict"] = EntailmentVerdict.ambiguity.value
    claim_payload["assessments"] = (assessment.model_dump(mode="json"),)
    verified_claim = VerifiedAtomicClaim(
        artifact_id=content_artifact_id(claim_payload),
        **claim_payload,
    )
    report_payload = answer.verification.model_dump(
        mode="json", exclude={"artifact_id"}
    )
    report_payload["claims"] = (verified_claim.model_dump(mode="json"),)
    verification = CitationVerificationReport(
        artifact_id=content_artifact_id(report_payload),
        **report_payload,
    )
    admission = GroundingAdmissionService().decide(
        claim_set=answer.claims,
        citation_set=answer.citations,
        verification_report=verification,
    )
    plan = _plan(answer, admission=admission, verification=verification)
    disambiguation = next(
        item
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.DISAMBIGUATION
    )

    assert disambiguation.material is True
    assert disambiguation.status is AnswerRequirementStatus.UNRESOLVED
    assert "exact entity scope qualifier" in str(disambiguation.query_text)
    assert disambiguation.source_gap_artifact_ids


def test_multi_hop_plan_links_cross_claim_dependencies() -> None:
    answer = _answer(
        "How do the two reported findings together explain the relationship?",
        _evidence(
            "method",
            "The first reported finding linked silica extraction to shorter fragments.",
            1,
        ),
        _evidence(
            "yield",
            "The second reported finding linked shorter fragments to higher endogenous DNA yield.",
            2,
        ),
    )
    claim_ids = tuple(item.artifact_id for item in answer.claims.claims)
    plan = _plan(answer, completed=claim_ids)
    cross_claim = next(
        item
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.CROSS_CLAIM_SYNTHESIS
    )
    finding_ids = {
        item.artifact_id
        for item in plan.requirements
        if item.kind is AnswerRequirementKind.FINDING
    }

    assert set(cross_claim.dependency_requirement_artifact_ids) == finding_ids
    assert cross_claim.status is AnswerRequirementStatus.SATISFIED


def test_out_of_scope_and_unsearchable_questions_do_not_issue_queries() -> None:
    answer = _answer(
        "What DNA yield was reported?",
        _evidence("yield", "Endogenous DNA yield reached 65 percent.", 1),
    )
    for request_status, expected in (
        (GroundingRequestStatus.out_of_scope, AnswerRequirementStatus.OUT_OF_SCOPE),
        (
            GroundingRequestStatus.fabricated_entity,
            AnswerRequirementStatus.UNSEARCHABLE,
        ),
    ):
        admission = GroundingAdmissionService().decide(
            claim_set=answer.claims,
            citation_set=answer.citations,
            verification_report=answer.verification,
            request_status=request_status,
        )
        plan = _plan(answer, admission=admission)

        assert plan.outcome is AnswerRequirementPlanOutcome.BLOCKED
        assert plan.search_requirement_artifact_ids == ()
        assert all(item.query_text is None for item in plan.requirements)
        assert all(
            item.status is expected for item in plan.requirements if item.material
        )
