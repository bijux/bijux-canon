# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for citation reachability against source-first evaluation truth."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from pydantic import ValidationError
import pytest

from bijux_canon_reason.evaluation import (
    AbstentionExpectation,
    AtomicClaimTruth,
    ClaimFaithfulnessEvaluator,
    ClaimFaithfulnessReport,
    ClaimFaithfulnessStatus,
    CitationIntegrityEvaluator,
    CitationIntegrityFailureCode,
    CitationIntegrityOwner,
    CitationIntegrityReport,
    CitationQualityEvaluator,
    CitationQualityFailureCode,
    CitationQualityReport,
    CitationTruthLabel,
    CitationTruthRelation,
    ClaimTruthClass,
    ConflictExpectation,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationSplit,
    ExactEvidenceLocator,
    QrelJudgment,
    SystemAnswerDisposition,
    SystemCitation,
    SystemClaim,
    SystemClaimDisposition,
    SystemOutput,
    TruthProvenance,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"


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


def _sources(case: EvaluationCaseTruth) -> dict[str, bytes]:
    locator = case.qrels[0].locator
    return {locator.source_uri: (REPO_ROOT / locator.source_uri).read_bytes()}


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
    )
    restarted = ClaimFaithfulnessReport.model_validate_json(report.model_dump_json())

    assert restarted == report
    assert report.passed
    assert report.judgments[0].status is ClaimFaithfulnessStatus.supported
    assert report.status_completeness.value == 1.0
    assert report.supported_claim_coverage.value == 1.0
    assert report.expected_claim_recall.value == 1.0
    assert report.nonexistent_evidence_claims.numerator == 0


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
    )

    assert report.judgments[0].status is ClaimFaithfulnessStatus.unverifiable
    assert report.status_completeness.value == 1.0
    assert report.expected_claim_recall.value == 0.0
    assert report.nonexistent_evidence_claims.numerator == 1
    assert not report.passed
