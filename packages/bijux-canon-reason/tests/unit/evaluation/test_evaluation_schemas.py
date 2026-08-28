# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Evaluation schemas exercised against the reviewed ancient-DNA truth."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema.validators import Draft202012Validator
from pydantic import ValidationError
import pytest

from bijux_canon_reason.evaluation import (
    EVALUATION_SCHEMA_CATALOG_VERSION,
    AbstentionExpectation,
    AtomicClaimTruth,
    CitationTruthLabel,
    ConfidenceInterval,
    ConflictExpectation,
    EvaluationCaseOutcome,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationReport,
    EvaluationSplit,
    ExactEvidenceLocator,
    MetricDirection,
    MetricObservation,
    QrelJudgment,
    ReviewerDecision,
    ReviewSubjectKind,
    ReviewVerdict,
    SystemAnswerDisposition,
    SystemCitation,
    SystemClaim,
    SystemClaimDisposition,
    SystemOutput,
    TruthProvenance,
    evaluation_json_schemas,
    write_evaluation_json_schemas,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _real_case() -> EvaluationCaseTruth:
    qrels = _jsonl(RESEARCH_ROOT / "truth/qrels.jsonl")
    claims = _jsonl(RESEARCH_ROOT / "truth/claim-truth.jsonl")
    claim = claims[0]
    evidence = claim["evidence"]
    qrel = next(record for record in qrels if record["qrel_id"] == evidence["qrel_id"])
    chunk = qrel["chunk"]
    qrel_provenance = TruthProvenance(
        reviewer_ids=(qrel["adjudicator_id"],),
        reviewed_on=date.fromisoformat(qrel["reviewed_on"]),
        review_method=qrel["review_method"],
        source_identity_sha256=qrel["source_sha256"],
        data_identity_sha256=qrel["qrel_identity_sha256"],
    )
    claim_provenance = TruthProvenance(
        reviewer_ids=(claim["reviewer_id"],),
        reviewed_on=date.fromisoformat(claim["reviewed_on"]),
        review_method=claim["review_method"],
        source_identity_sha256=claim["source_sha256"],
        data_identity_sha256=claim["claim_identity_sha256"],
    )
    query = EvaluationQuery(
        query_id=qrel["query_id"],
        text=qrel["query"],
        provenance=qrel_provenance,
    )
    judgment = QrelJudgment(
        qrel_id=qrel["qrel_id"],
        query_id=qrel["query_id"],
        relevance_grade=qrel["relevance_grade"],
        locator=ExactEvidenceLocator(
            locator_id=f"{qrel['source_id']}::chunk::{chunk['chunk_index']}",
            source_id=qrel["source_id"],
            source_uri=(
                f"examples/ancient-dna-research/corpus/sources/{qrel['source_id']}.xml"
            ),
            source_sha256=qrel["source_sha256"],
            chunk_id=chunk["chunk_id"],
            character_start=0,
            character_end=len(chunk["normalized_text"]),
            exact_text=chunk["normalized_text"],
            exact_text_sha256=chunk["normalized_text_sha256"],
        ),
        rationale=qrel["rationale"],
        provenance=qrel_provenance,
    )
    citation = CitationTruthLabel(
        citation_label_id=f"{claim['truth_id']}::citation",
        qrel_id=qrel["qrel_id"],
        relation=claim["evidence_relation"],
        rationale=claim["rationale"],
        provenance=claim_provenance,
    )
    atomic_claim = AtomicClaimTruth(
        claim_truth_id=claim["truth_id"],
        query_id=qrel["query_id"],
        statement=claim["claim"],
        claim_class=claim["claim_class"],
        expected_in_answer=claim["expected_in_answer"],
        abstention_expectation=AbstentionExpectation.prohibited,
        citations=(citation,),
        rationale=claim["rationale"],
        provenance=claim_provenance,
    )
    return EvaluationCaseTruth(
        case_id="adna-schema-case",
        split=EvaluationSplit.development,
        archetype="source-grounded",
        difficulty="hard",
        evidence_condition="direct",
        query=query,
        qrels=(judgment,),
        claims=(atomic_claim,),
        conflict=ConflictExpectation(
            conflict_expected=False,
            rationale="The selected reviewed claim has one direct supporting relation.",
        ),
        abstention_expectation=AbstentionExpectation.prohibited,
        provenance=claim_provenance,
    )


def test_case_truth_accepts_real_reviewed_qrel_claim_and_locator() -> None:
    case = _real_case()
    payload = case.model_dump(mode="json")

    assert payload["schema_version"] == "bijux.canon.evaluation.case-truth.v1"
    assert payload["heldout_labels_available_to_tuning"] is False
    assert payload["system_output_may_define_truth"] is False
    assert payload["qrels"][0]["locator"]["exact_text"]
    with pytest.raises(ValidationError, match="frozen"):
        case.case_id = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("heldout_labels_available_to_tuning", True),
        ("system_output_may_define_truth", True),
    ],
)
def test_case_truth_rejects_truth_leakage(field: str, value: bool) -> None:
    payload = _real_case().model_dump(mode="json")
    payload[field] = value

    with pytest.raises(ValidationError):
        EvaluationCaseTruth.model_validate(payload)


def test_case_truth_rejects_unknown_qrel_and_locator_tampering() -> None:
    payload = _real_case().model_dump(mode="json")
    broken_reference = deepcopy(payload)
    broken_reference["claims"][0]["citations"][0]["qrel_id"] = "unknown-qrel"
    with pytest.raises(ValidationError, match="unknown qrel"):
        EvaluationCaseTruth.model_validate(broken_reference)

    broken_locator = deepcopy(payload)
    broken_locator["qrels"][0]["locator"]["exact_text"] += " changed"
    with pytest.raises(ValidationError, match="bounds|hash"):
        EvaluationCaseTruth.model_validate(broken_locator)


def test_exact_locator_preserves_source_whitespace() -> None:
    exact_text = " retained source text "
    locator = ExactEvidenceLocator(
        locator_id="whitespace-locator",
        source_id="source-1",
        source_uri="file:///source.txt",
        source_sha256="0" * 64,
        chunk_id="chunk-1",
        character_start=5,
        character_end=5 + len(exact_text),
        exact_text=exact_text,
        exact_text_sha256=hashlib.sha256(exact_text.encode()).hexdigest(),
    )

    assert locator.exact_text == exact_text


def _system_output(case: EvaluationCaseTruth) -> SystemOutput:
    locator = case.qrels[0].locator
    citation = SystemCitation(
        citation_id="system-citation-1",
        source_id=locator.source_id,
        source_uri=locator.source_uri,
        source_sha256=locator.source_sha256,
        locator_id=locator.locator_id,
        exact_text_sha256=locator.exact_text_sha256,
        character_start=locator.character_start,
        character_end=locator.character_end,
    )
    claim = SystemClaim(
        claim_id="system-claim-1",
        statement=case.claims[0].statement,
        disposition=SystemClaimDisposition.asserted,
        citation_ids=(citation.citation_id,),
    )
    return SystemOutput(
        output_id="system-output-1",
        case_id=case.case_id,
        runtime_run_id="runtime-run-1",
        runtime_attempt_id="runtime-attempt-1",
        answer=claim.statement,
        disposition=SystemAnswerDisposition.answered,
        claims=(claim,),
        citations=(citation,),
        trace_identity_sha256="1" * 64,
    )


def test_system_output_is_separate_and_referentially_closed() -> None:
    output = _system_output(_real_case())
    assert output.system_output_may_define_truth is False

    payload = output.model_dump(mode="json")
    payload["truth"] = {"verdict": "pass"}
    with pytest.raises(ValidationError, match="Extra inputs"):
        SystemOutput.model_validate(payload)

    payload = output.model_dump(mode="json")
    payload["claims"][0]["citation_ids"] = ["missing-citation"]
    with pytest.raises(ValidationError, match="unknown citation"):
        SystemOutput.model_validate(payload)


def test_review_and_metric_report_preserve_arithmetic_and_lineage() -> None:
    case = _real_case()
    output = _system_output(case)
    decision = ReviewerDecision(
        decision_id="review-1",
        case_id=case.case_id,
        system_output_id=output.output_id,
        reviewer_id="reviewer-independent-1",
        reviewed_on=date(2026, 8, 22),
        subject_kind=ReviewSubjectKind.citation,
        subject_id=output.citations[0].citation_id,
        verdict=ReviewVerdict.pass_,
        label="direct-support",
        rationale="The emitted exact span directly supports the atomic system claim.",
        truth_identity_sha256="2" * 64,
        system_output_identity_sha256="3" * 64,
    )
    metric = MetricObservation(
        metric_id="citation-precision",
        metric_name="citation-precision",
        value=1.0,
        numerator=1.0,
        denominator=1.0,
        formula="directly supporting citations / emitted citations",
        direction=MetricDirection.higher_is_better,
        confidence_interval=ConfidenceInterval(
            level=0.95,
            lower=1.0,
            upper=1.0,
            method="exact single-case interval",
        ),
        case_ids=(case.case_id,),
        raw_sample_uri="artifact://evaluation/raw/citation-precision.jsonl",
    )
    report = EvaluationReport(
        report_id="report-1",
        split=case.split,
        outcomes=(
            EvaluationCaseOutcome(
                case_id=case.case_id,
                system_output_id=output.output_id,
                reviewer_decision_ids=(decision.decision_id,),
                metric_ids=(metric.metric_id,),
                passed=True,
            ),
        ),
        metrics=(metric,),
        raw_sample_uris=(metric.raw_sample_uri,),
        source_identity_sha256="4" * 64,
        data_identity_sha256="5" * 64,
        model_identity_sha256="6" * 64,
        config_identity_sha256="7" * 64,
        limitations=("One schema-contract case is not a benchmark estimate.",),
    )

    assert report.metrics[0].numerator == 1.0
    assert report.metrics[0].denominator == 1.0
    assert report.metrics[0].formula

    invalid_metric = metric.model_dump(mode="json")
    invalid_metric["value"] = 0.5
    with pytest.raises(ValidationError, match="confidence interval"):
        MetricObservation.model_validate(invalid_metric)


def test_schema_catalog_is_versioned_deterministic_and_valid(tmp_path: Path) -> None:
    first = evaluation_json_schemas()
    second = evaluation_json_schemas()

    assert EVALUATION_SCHEMA_CATALOG_VERSION.endswith(".v3")
    assert first == second
    assert set(first) == {
        "adjudication",
        "atomic-claim-truth",
        "case-outcome",
        "case-truth",
        "citation-truth",
        "claim-match-adjudication",
        "claim-match-report",
        "claim-match-review",
        "metric-observation",
        "product-case",
        "product-metric-definition",
        "product-metric-measurement",
        "product-metric-report",
        "qrel",
        "query",
        "report",
        "reviewer-decision",
        "system-output",
    }
    for schema in first.values():
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    written = write_evaluation_json_schemas(tmp_path / "schemas")
    assert [path.name for path in written] == [f"{name}.schema.json" for name in first]
    assert json.loads(written[0].read_text(encoding="utf-8")) == first["adjudication"]
