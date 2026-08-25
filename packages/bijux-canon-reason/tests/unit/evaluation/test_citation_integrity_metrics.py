# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for citation reachability against source-first evaluation truth."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from bijux_canon_reason.evaluation import (
    AbstentionExpectation,
    AbstentionSafetyCaseKind,
    AbstentionSafetyEvaluationError,
    AbstentionSafetyEvaluator,
    AbstentionSafetyInput,
    AbstentionSafetyReport,
    AtomicClaimTruth,
    CitationIntegrityEvaluator,
    CitationIntegrityFailureCode,
    CitationIntegrityOwner,
    CitationIntegrityReport,
    CitationQualityEvaluator,
    CitationQualityFailureCode,
    CitationQualityReport,
    CitationTruthLabel,
    CitationTruthRelation,
    ClaimFaithfulnessEvaluationError,
    ClaimFaithfulnessEvaluator,
    ClaimFaithfulnessReport,
    ClaimFaithfulnessStatus,
    ClaimMatchEvaluator,
    ClaimMatchRelation,
    ClaimMatchReport,
    ClaimQualifierAlignment,
    ClaimTruthClass,
    ConflictExpectation,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationSplit,
    ExactEvidenceLocator,
    PairedResearchBinding,
    PairedResearchCase,
    ProductAnswerDisposition,
    ProductExecutionStatus,
    QrelJudgment,
    ResearchUtilityEvaluator,
    ResearchUtilityReport,
    SystemAnswerDisposition,
    SystemCitation,
    SystemClaim,
    SystemClaimDisposition,
    SystemOutput,
    TruthProvenance,
    create_claim_match_adjudication,
    create_claim_match_review,
)
from bijux_canon_reason.research import (
    AnswerVerificationStatus,
    ConvergenceReason,
    ResearchConvergenceEvidence,
    create_research_convergence_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"


def _paired_binding() -> PairedResearchBinding:
    return PairedResearchBinding(
        question_sha256="7" * 64,
        corpus_artifact_id="sha256:" + "8" * 64,
        base_retrieval_artifact_id="sha256:" + "9" * 64,
        retrieval_config_sha256="a" * 64,
    )


def _convergence_evidence(
    *,
    material_requirement_count: int = 1,
    satisfied_requirement_artifact_ids: tuple[str, ...] = ("sha256:" + "1" * 64,),
    remaining_requirement_artifact_ids: tuple[str, ...] = (),
    material_candidate_count: int = 1,
    classified_candidate_count: int = 1,
    unresolved_classification_artifact_ids: tuple[str, ...] = (),
    blocking_gap_artifact_ids: tuple[str, ...] = (),
    unsearched_important_claim_artifact_ids: tuple[str, ...] = (),
    answer_verification_status: AnswerVerificationStatus = (
        AnswerVerificationStatus.admitted
    ),
    answer_revision_artifact_id: str | None = None,
) -> ResearchConvergenceEvidence:
    return create_research_convergence_evidence(
        current_graph_artifact_id="sha256:" + "2" * 64,
        material_requirement_count=material_requirement_count,
        satisfied_requirement_artifact_ids=satisfied_requirement_artifact_ids,
        remaining_requirement_artifact_ids=remaining_requirement_artifact_ids,
        material_candidate_count=material_candidate_count,
        classified_candidate_count=classified_candidate_count,
        unresolved_classification_artifact_ids=(unresolved_classification_artifact_ids),
        blocking_gap_artifact_ids=blocking_gap_artifact_ids,
        unsearched_important_claim_artifact_ids=(
            unsearched_important_claim_artifact_ids
        ),
        answer_verification_status=answer_verification_status,
        answer_revision_artifact_id=answer_revision_artifact_id,
        material_conflict_count=0,
        marginal_evidence_values=(0.5,),
    )


def _case() -> EvaluationCaseTruth:
    raw = json.loads(
        (RESEARCH_ROOT / "truth/qrels.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    chunk = raw["chunk"]
    exact_text = str(chunk["normalized_text"])
    provenance = TruthProvenance(
        reviewer_ids=(str(raw["adjudicator_id"]),),
        reviewed_on=date.fromisoformat(str(raw["reviewed_on"])),
        review_method=str(raw["review_method"]),
        source_identity_sha256=str(raw["source_sha256"]),
        data_identity_sha256=str(raw["qrel_identity_sha256"]),
    )
    locator = ExactEvidenceLocator(
        locator_id=f"{raw['source_id']}::chunk::{chunk['chunk_index']}",
        source_id=str(raw["source_id"]),
        source_uri=(
            f"examples/ancient-dna-research/corpus/sources/{raw['source_id']}.xml"
        ),
        source_sha256=str(raw["source_sha256"]),
        chunk_id=str(chunk["chunk_id"]),
        character_start=0,
        character_end=len(exact_text),
        exact_text=exact_text,
        exact_text_sha256=str(chunk["normalized_text_sha256"]),
    )
    qrel = QrelJudgment(
        qrel_id=str(raw["qrel_id"]),
        query_id=str(raw["query_id"]),
        relevance_grade=int(raw["relevance_grade"]),
        locator=locator,
        rationale=str(raw["rationale"]),
        provenance=provenance,
    )
    claim = AtomicClaimTruth(
        claim_truth_id="title-claim",
        query_id=qrel.query_id,
        statement=exact_text,
        claim_class=ClaimTruthClass.expected,
        expected_in_answer=True,
        abstention_expectation=AbstentionExpectation.prohibited,
        citations=(
            CitationTruthLabel(
                citation_label_id="title-citation-label",
                qrel_id=qrel.qrel_id,
                relation=CitationTruthRelation.supports,
                rationale="The article title is the exact reviewed span.",
                provenance=provenance,
            ),
        ),
        rationale="The title is retained as a source-routing claim.",
        provenance=provenance,
    )
    return EvaluationCaseTruth(
        case_id="real-citation-integrity",
        split=EvaluationSplit.development,
        archetype="source-grounded",
        difficulty="medium",
        evidence_condition="direct",
        query=EvaluationQuery(
            query_id=qrel.query_id,
            text=str(raw["query"]),
            provenance=provenance,
        ),
        qrels=(qrel,),
        claims=(claim,),
        conflict=ConflictExpectation(
            conflict_expected=False,
            rationale="This exact title locator has no conflicting truth label.",
        ),
        abstention_expectation=AbstentionExpectation.prohibited,
        provenance=provenance,
    )


def _output(case: EvaluationCaseTruth, citation: SystemCitation) -> SystemOutput:
    claim = SystemClaim(
        claim_id="system-claim",
        statement=case.claims[0].statement,
        disposition=SystemClaimDisposition.asserted,
        citation_ids=(citation.citation_id,),
    )
    return SystemOutput(
        output_id="system-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(claim,),
        citations=(citation,),
        trace_identity_sha256="f" * 64,
    )


def _citation(case: EvaluationCaseTruth, **changes: object) -> SystemCitation:
    locator = case.qrels[0].locator
    values: dict[str, object] = {
        "citation_id": "system-citation",
        "source_id": locator.source_id,
        "source_uri": locator.source_uri,
        "source_sha256": locator.source_sha256,
        "locator_id": locator.locator_id,
        "exact_text_sha256": locator.exact_text_sha256,
        "character_start": locator.character_start,
        "character_end": locator.character_end,
    }
    values.update(changes)
    return SystemCitation.model_validate(values)


def _chunk_citation(
    case: EvaluationCaseTruth,
    *,
    exact_text: str | None = None,
) -> SystemCitation:
    locator = case.qrels[0].locator
    quote = locator.exact_text if exact_text is None else exact_text
    return SystemCitation(
        schema_version="bijux.canon.evaluation.system-citation.v2",
        citation_id="chunk-system-citation",
        source_id=locator.source_id,
        source_uri=locator.source_uri,
        source_sha256=locator.source_sha256,
        locator_id="sha256:" + "4" * 64,
        exact_text_sha256=hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        character_start=0,
        character_end=len(quote),
        exact_text=quote,
        chunk_id=locator.chunk_id,
    )


def _sources(case: EvaluationCaseTruth) -> dict[str, bytes]:
    locator = case.qrels[0].locator
    return {locator.source_uri: (REPO_ROOT / locator.source_uri).read_bytes()}


def _matching(
    case: EvaluationCaseTruth,
    output: SystemOutput,
    *,
    force_truth: bool | None = None,
) -> ClaimMatchReport:
    truth_statements = {item.statement for item in case.claims}
    reviews = []
    for claim in output.claims:
        matched = (
            claim.statement in truth_statements if force_truth is None else force_truth
        )
        truth = case.claims[0] if matched else None
        reviews.append(
            create_claim_match_review(
                case=case,
                output=output,
                system_claim_id=claim.claim_id,
                truth_claim_id=None if truth is None else truth.claim_truth_id,
                relation=(
                    ClaimMatchRelation.unrelated
                    if truth is None
                    else ClaimMatchRelation.qualified_equivalent
                ),
                qualifier_alignment=ClaimQualifierAlignment(
                    entity=matched,
                    scope=matched,
                    quantity=matched,
                    modality=matched,
                    negation=matched,
                ),
                reviewed_qrel_ids=(
                    ()
                    if truth is None
                    else tuple(item.qrel_id for item in truth.citations)
                ),
                reviewer_id="independent-output-reviewer",
                reviewed_on=date(2026, 8, 24),
                rationale=(
                    "The claim is unrelated to the frozen expected proposition."
                    if truth is None
                    else "The paraphrase retains entity, scope, quantity, modality, and negation."
                ),
            )
        )
    return ClaimMatchEvaluator().evaluate(
        case=case,
        output=output,
        reviews=tuple(reviews),
    )


def test_real_source_citation_resolves_locator_span_text_and_hash() -> None:
    case = _case()
    citation = _citation(case)

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=_output(case, citation),
        source_payloads=_sources(case),
    )
    restarted = CitationIntegrityReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.verified_citations == report.total_citations == 1
    assert report.integrity_ratio == 1.0
    assert report.failures == ()


def test_real_chunk_citation_verifies_emitted_quote_without_truth_locator_equality() -> (
    None
):
    case = _case()
    citation = _chunk_citation(case)
    output = _output(case, citation)

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )
    matching = _matching(case, output)
    quality = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=report,
        matching=matching,
    )
    faithfulness = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=report,
        matching=matching,
    )

    assert citation.locator_id != case.qrels[0].locator.locator_id
    assert report.passed
    assert report.verified_citations == 1
    assert quality.passed
    assert faithfulness.passed


def test_chunk_citation_rejects_quote_absent_from_immutable_source() -> None:
    case = _case()
    citation = _chunk_citation(
        case,
        exact_text="This fabricated quote is absent from the immutable article.",
    )

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=_output(case, citation),
        source_payloads=_sources(case),
    )

    assert not report.passed
    assert report.failures[0].code is (
        CitationIntegrityFailureCode.source_text_unreachable
    )


def test_emitted_binding_failures_are_owned_by_reason() -> None:
    case = _case()
    citation = _citation(
        case,
        source_id="wrong-source",
        exact_text_sha256="0" * 64,
        character_end=case.qrels[0].locator.character_end + 1,
    )

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=_output(case, citation),
        source_payloads=_sources(case),
    )

    assert not report.passed
    assert report.integrity_ratio == 0.0
    assert {failure.code for failure in report.failures} == {
        CitationIntegrityFailureCode.source_binding_mismatch,
        CitationIntegrityFailureCode.span_mismatch,
        CitationIntegrityFailureCode.text_hash_mismatch,
    }
    assert {failure.owner for failure in report.failures} == {
        CitationIntegrityOwner.reason
    }


@pytest.mark.parametrize(
    ("payloads", "code"),
    [
        ({}, CitationIntegrityFailureCode.source_unavailable),
        (
            {"source": b"tampered"},
            CitationIntegrityFailureCode.source_hash_mismatch,
        ),
    ],
)
def test_source_failures_are_owned_by_ingest(
    payloads: dict[str, bytes],
    code: CitationIntegrityFailureCode,
) -> None:
    case = _case()
    locator = case.qrels[0].locator
    bound = {} if not payloads else {locator.source_uri: payloads["source"]}

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=_output(case, _citation(case)),
        source_payloads=bound,
    )

    assert report.failures[0].code is code
    assert report.failures[0].owner is CitationIntegrityOwner.ingest


def test_no_citation_output_is_explicit_and_report_identity_fails_closed() -> None:
    case = _case()
    output = SystemOutput(
        output_id="abstained-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer="",
        disposition=SystemAnswerDisposition.abstained,
        abstention_reason="No admitted evidence was available.",
        trace_identity_sha256="e" * 64,
    )

    report = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads={},
    )

    assert report.passed
    assert report.no_citations_produced
    assert report.total_citations == report.verified_citations == 0
    drifted = report.model_dump(mode="json")
    drifted["artifact_id"] = "sha256:" + "0" * 64
    with pytest.raises(ValidationError, match="identity"):
        CitationIntegrityReport.model_validate(drifted)


def test_reviewed_claim_span_relation_earns_precision_and_recall_credit() -> None:
    case = _case()
    output = _output(case, _citation(case))
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )
    restarted = CitationQualityReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.precision.numerator == report.precision.denominator == 1
    assert report.precision.value == 1.0
    assert report.recall.numerator == report.recall.denominator == 1
    assert report.recall.value == 1.0
    assert report.failures == ()


def test_attached_citation_gets_no_credit_without_reviewed_claim_relation() -> None:
    case = _case()
    citation = _citation(case)
    unrelated_claim = SystemClaim(
        claim_id="unreviewed-system-claim",
        statement="An unreviewed claim cannot inherit truth from citation presence.",
        disposition=SystemClaimDisposition.asserted,
        citation_ids=(citation.citation_id,),
    )
    output = SystemOutput(
        output_id="unreviewed-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=unrelated_claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(unrelated_claim,),
        citations=(citation,),
        trace_identity_sha256="d" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert integrity.passed
    assert not report.passed
    assert report.precision.numerator == 0
    assert report.precision.denominator == 1
    assert report.recall.numerator == 0
    assert report.recall.denominator == 1
    assert {failure.code for failure in report.failures} == {
        CitationQualityFailureCode.claim_not_in_truth,
        CitationQualityFailureCode.expected_relation_missing,
    }


def test_empty_citations_keep_zero_precision_denominator_and_expected_recall() -> None:
    case = _case()
    output = SystemOutput(
        output_id="empty-citation-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer="",
        disposition=SystemAnswerDisposition.abstained,
        abstention_reason="No answer was produced.",
        trace_identity_sha256="c" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads={},
    )

    report = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert not report.passed
    assert report.precision.denominator == 0
    assert report.precision.value == 0.0
    assert report.precision.confidence_interval.lower == 0.0
    assert report.precision.confidence_interval.upper == 1.0
    assert report.recall.denominator == 1
    assert report.recall.value == 0.0


def test_duplicate_emission_does_not_multiply_reviewed_relation_credit() -> None:
    case = _case()
    citation = _citation(case)
    claims = tuple(
        SystemClaim(
            claim_id=f"system-claim-{index}",
            statement=case.claims[0].statement,
            disposition=SystemClaimDisposition.asserted,
            citation_ids=(citation.citation_id,),
        )
        for index in range(2)
    )
    output = SystemOutput(
        output_id="duplicate-relation-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=case.claims[0].statement,
        disposition=SystemAnswerDisposition.answered,
        claims=claims,
        citations=(citation,),
        trace_identity_sha256="b" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert report.precision.numerator == 1
    assert report.precision.denominator == 2
    assert report.recall.numerator == report.recall.denominator == 1
    assert [failure.code for failure in report.failures] == [
        CitationQualityFailureCode.duplicate_reviewed_relation
    ]


def test_real_reviewed_claim_is_faithful_only_with_reachable_related_evidence() -> None:
    case = _case()
    output = _output(case, _citation(case))
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )
    restarted = ClaimFaithfulnessReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.judgments[0].status is ClaimFaithfulnessStatus.supported
    assert report.status_completeness.value == 1.0
    assert report.supported_claim_coverage.value == 1.0
    assert report.expected_claim_recall.value == 1.0
    assert report.nonexistent_evidence_claims.numerator == 0


def test_qualifier_complete_paraphrase_earns_claim_and_citation_credit() -> None:
    case = _case()
    citation = _citation(case)
    claim = SystemClaim(
        claim_id="paraphrased-system-claim",
        statement=(
            "Tissue-specific transcriptomes survived in RNA from historical canids "
            "and a Late Pleistocene canid preserved in permafrost."
        ),
        disposition=SystemClaimDisposition.qualified,
        citation_ids=(citation.citation_id,),
    )
    output = SystemOutput(
        output_id="paraphrased-system-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(claim,),
        citations=(citation,),
        trace_identity_sha256="1" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )
    matching = _matching(case, output, force_truth=True)

    citation_report = CitationQualityEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=matching,
    )
    faithfulness = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=matching,
    )

    assert claim.statement != case.claims[0].statement
    assert citation_report.passed
    assert faithfulness.passed
    assert matching.outcomes[0].relation is ClaimMatchRelation.qualified_equivalent


def test_overgeneralized_claim_gets_no_credit_despite_valid_citation() -> None:
    case = _case()
    citation = _citation(case)
    claim = SystemClaim(
        claim_id="overgeneralized-system-claim",
        statement="Ancient RNA always survives in every canid tissue and environment.",
        disposition=SystemClaimDisposition.asserted,
        citation_ids=(citation.citation_id,),
    )
    output = SystemOutput(
        output_id="overgeneralized-system-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(claim,),
        citations=(citation,),
        trace_identity_sha256="2" * 64,
    )
    review = create_claim_match_review(
        case=case,
        output=output,
        system_claim_id=claim.claim_id,
        truth_claim_id=case.claims[0].claim_truth_id,
        relation=ClaimMatchRelation.overgeneralized,
        qualifier_alignment=ClaimQualifierAlignment(
            entity=True,
            scope=False,
            quantity=False,
            modality=False,
            negation=True,
        ),
        reviewed_qrel_ids=(case.qrels[0].qrel_id,),
        reviewer_id="independent-output-reviewer",
        reviewed_on=date(2026, 8, 24),
        rationale="The emitted universal claim drops the reviewed specimen and tissue scope.",
    )
    matching = ClaimMatchEvaluator().evaluate(
        case=case,
        output=output,
        reviews=(review,),
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    faithfulness = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=matching,
    )

    assert integrity.passed
    assert not faithfulness.passed
    assert faithfulness.judgments[0].status is ClaimFaithfulnessStatus.ambiguous
    assert matching.errors[0].kind.value == "overgeneralized"


def test_claim_review_is_bound_to_exact_system_output_not_answer_keywords() -> None:
    case = _case()
    output = _output(case, _citation(case))
    matching = _matching(case, output)
    altered = output.model_copy(
        update={"answer": "The output changed after independent semantic review."}
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=altered,
        source_payloads=_sources(case),
    )

    with pytest.raises(
        ClaimFaithfulnessEvaluationError,
        match="another truth or system output",
    ):
        ClaimFaithfulnessEvaluator().evaluate(
            case=case,
            output=altered,
            integrity=integrity,
            matching=matching,
        )


def test_unadjudicated_reviewer_disagreement_remains_visible_and_unresolved() -> None:
    case = _case()
    output = _output(case, _citation(case))
    agreeing = create_claim_match_review(
        case=case,
        output=output,
        system_claim_id=output.claims[0].claim_id,
        truth_claim_id=case.claims[0].claim_truth_id,
        relation=ClaimMatchRelation.qualified_equivalent,
        qualifier_alignment=ClaimQualifierAlignment(
            entity=True,
            scope=True,
            quantity=True,
            modality=True,
            negation=True,
        ),
        reviewed_qrel_ids=(case.qrels[0].qrel_id,),
        reviewer_id="independent-reviewer-one",
        reviewed_on=date(2026, 8, 24),
        rationale="The first reviewer considers every material qualifier retained.",
    )
    disagreeing = create_claim_match_review(
        case=case,
        output=output,
        system_claim_id=output.claims[0].claim_id,
        truth_claim_id=case.claims[0].claim_truth_id,
        relation=ClaimMatchRelation.overgeneralized,
        qualifier_alignment=ClaimQualifierAlignment(
            entity=True,
            scope=False,
            quantity=True,
            modality=True,
            negation=True,
        ),
        reviewed_qrel_ids=(case.qrels[0].qrel_id,),
        reviewer_id="independent-reviewer-two",
        reviewed_on=date(2026, 8, 24),
        rationale="The second reviewer finds the source population scope missing.",
    )

    matching = ClaimMatchEvaluator().evaluate(
        case=case,
        output=output,
        reviews=(agreeing, disagreeing),
    )

    assert matching.outcomes[0].reviewer_disagreement
    assert matching.outcomes[0].unresolved
    assert matching.outcomes[0].relation is ClaimMatchRelation.ambiguous
    assert matching.errors[0].kind.value == "reviewer_disagreement"

    adjudication = create_claim_match_adjudication(
        reviews=(agreeing, disagreeing),
        truth_claim_id=case.claims[0].claim_truth_id,
        relation=ClaimMatchRelation.qualified_equivalent,
        qualifier_alignment=ClaimQualifierAlignment(
            entity=True,
            scope=True,
            quantity=True,
            modality=True,
            negation=True,
        ),
        reviewed_qrel_ids=(case.qrels[0].qrel_id,),
        adjudicator_id="independent-adjudicator",
        adjudicated_on=date(2026, 8, 24),
        rationale="Source review confirms that the emitted title retains its source scope.",
    )
    resolved = ClaimMatchEvaluator().evaluate(
        case=case,
        output=output,
        reviews=(agreeing, disagreeing),
        adjudications=(adjudication,),
    )

    assert resolved.outcomes[0].reviewer_disagreement
    assert not resolved.outcomes[0].unresolved
    assert resolved.outcomes[0].admitted_equivalence
    assert resolved.outcomes[0].adjudication_artifact_id == adjudication.artifact_id


@pytest.mark.parametrize(
    ("relation", "claim_class", "expected_status"),
    [
        (
            CitationTruthRelation.opposes,
            ClaimTruthClass.opposed,
            ClaimFaithfulnessStatus.opposed,
        ),
        (
            CitationTruthRelation.limits,
            ClaimTruthClass.forbidden,
            ClaimFaithfulnessStatus.ambiguous,
        ),
    ],
)
def test_reviewed_relation_classifies_opposed_and_ambiguous_claims(
    relation: CitationTruthRelation,
    claim_class: ClaimTruthClass,
    expected_status: ClaimFaithfulnessStatus,
) -> None:
    original = _case()
    label = original.claims[0].citations[0].model_copy(update={"relation": relation})
    truth_claim = original.claims[0].model_copy(
        update={
            "claim_class": claim_class,
            "expected_in_answer": False,
            "abstention_expectation": AbstentionExpectation.required,
            "citations": (label,),
        }
    )
    case = original.model_copy(
        update={
            "claims": (truth_claim,),
            "abstention_expectation": AbstentionExpectation.required,
        }
    )
    output = _output(case, _citation(case))
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert report.judgments[0].status is expected_status
    assert report.status_completeness.value == 1.0
    assert report.supported_claim_coverage.value == 0.0


def test_verified_but_unrelated_evidence_is_irrelevant_not_supported() -> None:
    original = _case()
    original_qrel = original.qrels[0]
    unrelated_locator = original_qrel.locator.model_copy(
        update={"locator_id": "unrelated-reviewed-locator"}
    )
    unrelated_qrel = original_qrel.model_copy(
        update={"qrel_id": "unrelated-qrel", "locator": unrelated_locator}
    )
    case = original.model_copy(update={"qrels": original.qrels + (unrelated_qrel,)})
    citation = _citation(case, locator_id=unrelated_locator.locator_id)
    output = _output(case, citation)
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=_sources(case),
    )

    report = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert integrity.passed
    assert report.judgments[0].status is ClaimFaithfulnessStatus.irrelevant
    assert report.supported_claim_coverage.numerator == 0


def test_unknown_claim_and_missing_evidence_are_retained_as_failures() -> None:
    case = _case()
    claim = SystemClaim(
        claim_id="invented-claim",
        statement="This atomic claim has no reviewed truth or evidence.",
        disposition=SystemClaimDisposition.asserted,
    )
    output = SystemOutput(
        output_id="invented-output",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer=claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(claim,),
        trace_identity_sha256="a" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads={},
    )

    report = ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )

    assert report.judgments[0].status is ClaimFaithfulnessStatus.unverifiable
    assert report.status_completeness.value == 1.0
    assert report.expected_claim_recall.value == 0.0
    assert report.nonexistent_evidence_claims.numerator == 1
    assert not report.passed


def _safety_input(kind: AbstentionSafetyCaseKind) -> AbstentionSafetyInput:
    original = _case()
    label = (
        original.claims[0]
        .citations[0]
        .model_copy(update={"relation": CitationTruthRelation.opposes})
    )
    opposed_claim = original.claims[0].model_copy(
        update={
            "claim_class": ClaimTruthClass.opposed,
            "expected_in_answer": False,
            "abstention_expectation": AbstentionExpectation.required,
            "citations": (label,),
        }
    )
    case = original.model_copy(
        update={
            "case_id": f"safety-{kind.value}",
            "archetype": kind.value,
            "claims": (opposed_claim,),
            "abstention_expectation": AbstentionExpectation.required,
        }
    )
    output = SystemOutput(
        output_id=f"output-{kind.value}",
        case_id=case.case_id,
        runtime_run_id="runtime-run",
        runtime_attempt_id="runtime-attempt",
        answer="",
        disposition=SystemAnswerDisposition.abstained,
        abstention_reason=f"The {kind.value} case cannot be answered safely.",
        trace_identity_sha256="9" * 64,
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads={},
    )
    return AbstentionSafetyInput(
        kind=kind,
        truth=case,
        output=output,
        citation_integrity=integrity,
    )


def test_all_negative_strata_abstain_without_leaking_scope_or_citations() -> None:
    cases = tuple(_safety_input(kind) for kind in AbstentionSafetyCaseKind)

    report = AbstentionSafetyEvaluator().evaluate(cases)
    restarted = AbstentionSafetyReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.correct_abstention.numerator == 5
    assert report.correct_abstention.denominator == 5
    assert report.scope_enforcement.value == 1.0
    assert report.invented_citations.numerator == 0
    assert report.invented_citations.denominator == 0


def test_fabricated_answer_and_locator_fail_without_denominator_dropping() -> None:
    cases = [_safety_input(kind) for kind in AbstentionSafetyCaseKind]
    original = cases[2]
    citation = _citation(original.truth, locator_id="fabricated-locator")
    output = _output(original.truth, citation).model_copy(
        update={"output_id": "fabricated-answer-output"}
    )
    integrity = CitationIntegrityEvaluator().evaluate(
        case=original.truth,
        output=output,
        source_payloads=_sources(original.truth),
    )
    cases[2] = AbstentionSafetyInput(
        kind=AbstentionSafetyCaseKind.fabricated_entity,
        truth=original.truth,
        output=output,
        citation_integrity=integrity,
    )

    report = AbstentionSafetyEvaluator().evaluate(tuple(cases))

    assert not report.passed
    assert report.correct_abstention.numerator == 4
    assert report.correct_abstention.denominator == 5
    assert report.scope_enforcement.numerator == 4
    assert report.scope_enforcement.denominator == 5
    assert report.invented_citations.numerator == 1
    assert report.invented_citations.denominator == 1
    assert report.outcomes[2].invented_citation_ids == (citation.citation_id,)


def test_safety_suite_refuses_missing_negative_strata() -> None:
    with pytest.raises(AbstentionSafetyEvaluationError, match="missing required"):
        AbstentionSafetyEvaluator().evaluate(
            (_safety_input(AbstentionSafetyCaseKind.unanswerable),)
        )


def _faithfulness(
    case: EvaluationCaseTruth,
    output: SystemOutput,
    sources: dict[str, bytes],
) -> ClaimFaithfulnessReport:
    integrity = CitationIntegrityEvaluator().evaluate(
        case=case,
        output=output,
        source_payloads=sources,
    )
    return ClaimFaithfulnessEvaluator().evaluate(
        case=case,
        output=output,
        integrity=integrity,
        matching=_matching(case, output),
    )


def test_bounded_research_reports_paired_quality_cost_latency_and_convergence() -> None:
    case = _case()
    rag_output = SystemOutput(
        output_id="one-pass-output",
        case_id=case.case_id,
        runtime_run_id="rag-run",
        runtime_attempt_id="rag-attempt",
        answer="",
        disposition=SystemAnswerDisposition.abstained,
        abstention_reason="One-pass retrieval did not establish the expected claim.",
        trace_identity_sha256="8" * 64,
    )
    rar_output = _output(case, _citation(case)).model_copy(
        update={"output_id": "bounded-research-output"}
    )
    paired = PairedResearchCase(
        case_id=case.case_id,
        rag_binding=_paired_binding(),
        rar_binding=_paired_binding(),
        source_identity_sha256="a" * 64,
        model_identity_sha256="b" * 64,
        config_identity_sha256="c" * 64,
        rag_faithfulness=_faithfulness(case, rag_output, {}),
        rar_faithfulness=_faithfulness(case, rar_output, _sources(case)),
        expected_counterevidence_qrel_ids=(case.qrels[0].qrel_id,),
        rar_counterevidence_qrel_ids=(case.qrels[0].qrel_id,),
        rar_convergence_evidence=_convergence_evidence(
            answer_revision_artifact_id="sha256:" + "d" * 64
        ),
        rar_convergence_reasons=(ConvergenceReason.coverage_and_answerability,),
        rar_answer_changed=True,
        rag_cost_usd=0.01,
        rar_cost_usd=0.03,
        rag_latency_ms=10,
        rar_latency_ms=30,
        rar_iterations=2,
        rag_tool_calls=1,
        rar_tool_calls=1,
    )

    report = ResearchUtilityEvaluator().evaluate((paired,))
    restarted = ResearchUtilityReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.counterevidence_recall.value == 1.0
    assert report.expected_claim_recall_gain.value == 1.0
    assert report.unsupported_claim_rate_delta.value == 0.0
    assert report.rag_total_cost_usd == 0.01
    assert report.rar_total_latency_ms == 30
    assert report.rar_total_iterations == 2
    assert report.rag_total_tool_calls == 1
    assert report.rar_total_tool_calls == 1
    assert report.requirement_coverage.value == 1.0
    assert report.classification_completeness.value == 1.0
    assert report.completed_material_closure.value == 1.0


def test_bounded_research_no_change_case_requires_no_counterevidence() -> None:
    case = _case()
    rag_output = _output(case, _citation(case)).model_copy(
        update={"output_id": "verified-rag-output"}
    )
    rar_output = rag_output.model_copy(update={"output_id": "preserved-rar-output"})
    paired = PairedResearchCase(
        case_id=case.case_id,
        rag_binding=_paired_binding(),
        rar_binding=_paired_binding(),
        source_identity_sha256="a" * 64,
        model_identity_sha256="b" * 64,
        config_identity_sha256="c" * 64,
        rag_faithfulness=_faithfulness(case, rag_output, _sources(case)),
        rar_faithfulness=_faithfulness(case, rar_output, _sources(case)),
        expected_counterevidence_qrel_ids=(),
        rar_counterevidence_qrel_ids=(),
        rar_convergence_evidence=_convergence_evidence(
            material_candidate_count=0,
            classified_candidate_count=0,
        ),
        rar_convergence_reasons=(ConvergenceReason.stable_graph,),
        rar_answer_changed=False,
        rag_cost_usd=0.0,
        rar_cost_usd=0.0,
        rag_latency_ms=10,
        rar_latency_ms=11,
        rar_iterations=1,
        rag_tool_calls=1,
        rar_tool_calls=0,
    )

    report = ResearchUtilityEvaluator().evaluate((paired,))

    assert report.counterevidence_recall.value == 1.0
    assert report.outcomes[0].counterevidence_expected == 0
    assert not report.outcomes[0].answer_changed
    assert report.outcomes[0].revision_artifact_id is None
    assert report.completed_material_closure.value == 1.0


def test_paired_research_rejects_different_base_retrieval() -> None:
    case = _case()
    output = _output(case, _citation(case))
    faithfulness = _faithfulness(case, output, _sources(case))
    rar_output = output.model_copy(update={"output_id": "different-output"})
    rar_faithfulness = _faithfulness(case, rar_output, _sources(case))

    with pytest.raises(ValidationError, match="must share question, corpus, retrieval"):
        PairedResearchCase(
            case_id=case.case_id,
            rag_binding=_paired_binding(),
            rar_binding=_paired_binding().model_copy(
                update={"base_retrieval_artifact_id": "sha256:" + "0" * 64}
            ),
            source_identity_sha256="a" * 64,
            model_identity_sha256="b" * 64,
            config_identity_sha256="c" * 64,
            rag_faithfulness=faithfulness,
            rar_faithfulness=rar_faithfulness,
            expected_counterevidence_qrel_ids=(),
            rar_counterevidence_qrel_ids=(),
            rar_convergence_evidence=_convergence_evidence(
                material_requirement_count=0,
                satisfied_requirement_artifact_ids=(),
                material_candidate_count=0,
                classified_candidate_count=0,
                answer_verification_status=AnswerVerificationStatus.not_run,
            ),
            rar_convergence_reasons=(ConvergenceReason.explicit_insufficiency,),
            rar_answer_changed=False,
            rag_cost_usd=0.0,
            rar_cost_usd=0.0,
            rag_latency_ms=1,
            rar_latency_ms=1,
            rar_iterations=1,
            rag_tool_calls=0,
            rar_tool_calls=0,
        )


def test_bounded_research_failure_keeps_pair_and_negative_deltas() -> None:
    case = _case()
    rag_output = _output(case, _citation(case)).model_copy(
        update={"output_id": "supported-one-pass-output"}
    )
    citation = _citation(case)
    unsupported_claim = SystemClaim(
        claim_id="unsupported-research-claim",
        statement="Bounded research invented an unreviewed conclusion.",
        disposition=SystemClaimDisposition.asserted,
        citation_ids=(citation.citation_id,),
    )
    rar_output = SystemOutput(
        output_id="regressed-research-output",
        case_id=case.case_id,
        runtime_run_id="rar-run",
        runtime_attempt_id="rar-attempt",
        answer=unsupported_claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(unsupported_claim,),
        citations=(citation,),
        trace_identity_sha256="6" * 64,
    )
    paired = PairedResearchCase(
        case_id=case.case_id,
        rag_binding=_paired_binding(),
        rar_binding=_paired_binding(),
        source_identity_sha256="a" * 64,
        model_identity_sha256="b" * 64,
        config_identity_sha256="c" * 64,
        rag_faithfulness=_faithfulness(case, rag_output, _sources(case)),
        rar_faithfulness=_faithfulness(case, rar_output, _sources(case)),
        expected_counterevidence_qrel_ids=(case.qrels[0].qrel_id,),
        rar_counterevidence_qrel_ids=(),
        rar_convergence_evidence=_convergence_evidence(
            satisfied_requirement_artifact_ids=(),
            remaining_requirement_artifact_ids=("sha256:" + "3" * 64,),
            classified_candidate_count=0,
            unresolved_classification_artifact_ids=("sha256:" + "e" * 64,),
            blocking_gap_artifact_ids=(
                "sha256:" + "3" * 64,
                "sha256:" + "e" * 64,
                "sha256:" + "f" * 64,
            ),
            unsearched_important_claim_artifact_ids=("sha256:" + "f" * 64,),
            answer_verification_status=AnswerVerificationStatus.not_run,
        ),
        rar_convergence_reasons=(ConvergenceReason.tool_limit,),
        rar_answer_changed=False,
        rag_cost_usd=0.01,
        rar_cost_usd=0.04,
        rag_latency_ms=10,
        rar_latency_ms=40,
        rar_iterations=3,
        rag_tool_calls=1,
        rar_tool_calls=2,
        rar_execution_status=ProductExecutionStatus.budget_exhausted,
        rar_failure_code="research-budget-exhausted",
        rar_answer_disposition=ProductAnswerDisposition.not_produced,
    )

    report = ResearchUtilityEvaluator().evaluate((paired,))

    assert not report.passed
    assert report.counterevidence_recall.value == 0.0
    assert report.expected_claim_recall_gain.value == -1.0
    assert report.unsupported_claim_rate_delta.value == 1.0
    assert len(report.outcomes) == 1
    unconditional = {
        item.definition.metric_id: item for item in report.unconditional_metrics.metrics
    }
    assert unconditional["completion.product-success-rate"].value == 0.0
    assert unconditional["counterevidence.recall"].value == 0.0
    assert unconditional["revision.expected-claim-recall-gain"].value == -1.0


def test_budget_exhaustion_cannot_inherit_successful_partial_output_scores() -> None:
    case = _case()
    rag_output = SystemOutput(
        output_id="empty-one-pass-output",
        case_id=case.case_id,
        runtime_run_id="rag-run",
        runtime_attempt_id="rag-attempt",
        answer="",
        disposition=SystemAnswerDisposition.abstained,
        abstention_reason="One-pass evidence was insufficient.",
        trace_identity_sha256="8" * 64,
    )
    apparently_good_rar = _output(case, _citation(case)).model_copy(
        update={"output_id": "partial-research-output"}
    )
    paired = PairedResearchCase(
        case_id=case.case_id,
        rag_binding=_paired_binding(),
        rar_binding=_paired_binding(),
        source_identity_sha256="a" * 64,
        model_identity_sha256="b" * 64,
        config_identity_sha256="c" * 64,
        rag_faithfulness=_faithfulness(case, rag_output, {}),
        rar_faithfulness=_faithfulness(case, apparently_good_rar, _sources(case)),
        expected_counterevidence_qrel_ids=(case.qrels[0].qrel_id,),
        rar_counterevidence_qrel_ids=(case.qrels[0].qrel_id,),
        rar_convergence_evidence=_convergence_evidence(
            satisfied_requirement_artifact_ids=(),
            remaining_requirement_artifact_ids=("sha256:" + "3" * 64,),
            blocking_gap_artifact_ids=(
                "sha256:" + "3" * 64,
                "sha256:" + "f" * 64,
            ),
            unsearched_important_claim_artifact_ids=("sha256:" + "f" * 64,),
            answer_revision_artifact_id="sha256:" + "d" * 64,
        ),
        rar_convergence_reasons=(ConvergenceReason.tool_limit,),
        rar_answer_changed=True,
        rag_cost_usd=0.0,
        rar_cost_usd=0.0,
        rag_latency_ms=10,
        rar_latency_ms=20,
        rar_iterations=2,
        rag_tool_calls=0,
        rar_tool_calls=2,
        rar_execution_status=ProductExecutionStatus.budget_exhausted,
        rar_failure_code="research-budget-exhausted",
        rar_answer_disposition=ProductAnswerDisposition.not_produced,
    )

    report = ResearchUtilityEvaluator().evaluate((paired,))

    assert not report.passed
    assert report.counterevidence_recall.value == 0.0
    assert report.expected_claim_recall_gain.value == 0.0
    assert report.unsupported_claim_rate_delta.value == 1.0
    assert report.outcomes[0].rar_execution_status is (
        ProductExecutionStatus.budget_exhausted
    )
