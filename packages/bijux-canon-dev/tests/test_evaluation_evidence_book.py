"""Tests for deterministic evaluation evidence-book generation."""

from __future__ import annotations

from dataclasses import replace
import json
from typing import cast

import pytest

from bijux_canon_dev.quality import (
    EvaluationEvidenceBookGenerator,
    EvidenceBookAggregate,
    EvidenceBookCaseResult,
    EvidenceBookIdentities,
)


def _inputs() -> dict[str, object]:
    return {
        "source_commit": "current-head",
        "current_commit": "current-head",
        "identities": EvidenceBookIdentities(
            source_sha256="1" * 64,
            data_sha256="2" * 64,
            model_sha256="3" * 64,
            config_sha256="4" * 64,
        ),
        "cases": (
            EvidenceBookCaseResult(
                case_id="real-case-001",
                passed=True,
                metrics={
                    "retrieval.recall-at-5": 1.0,
                    "completion.product-success-rate": 1.0,
                },
            ),
            EvidenceBookCaseResult(
                case_id="real-case-002",
                passed=False,
                metrics={
                    "retrieval.recall-at-5": 0.0,
                    "completion.product-success-rate": 0.0,
                },
                execution_status="failed",
                failure_code="retrieval-backend-failed",
                label_completeness=0.5,
                errors=("expected qrel was not retrieved",),
            ),
        ),
        "aggregates": (
            EvidenceBookAggregate(
                metric_id="retrieval.recall-at-5",
                definition_version=1,
                aggregation="macro-mean",
                population_unit="unique reviewed query",
                semantic_denominator="all unique reviewed queries",
                case_ids=("real-case-001", "real-case-002"),
                numerator=1.0,
                denominator=2.0,
                value=0.5,
                confidence_lower=0.1,
                confidence_upper=0.9,
                confidence_method="Wilson score interval",
                population_standard_deviation=0.5,
                worst_case_ids=("real-case-002",),
                baseline_value=0.4,
            ),
            EvidenceBookAggregate(
                metric_id="completion.product-success-rate",
                definition_version=1,
                aggregation="macro-mean",
                population_unit="unique attempted product case",
                semantic_denominator="all attempted cases including failures",
                case_ids=("real-case-001", "real-case-002"),
                numerator=1.0,
                denominator=2.0,
                value=0.5,
                confidence_lower=0.1,
                confidence_upper=0.9,
                confidence_method="empirical 95% interval",
                population_standard_deviation=0.5,
                worst_case_ids=("real-case-002",),
                baseline_value=None,
            ),
        ),
        "limitations": ("Two cases are insufficient for a release estimate.",),
        "commands": ("bijux evaluation run --split heldout",),
    }


def test_evidence_book_regenerates_index_cases_and_summary(tmp_path) -> None:
    generator = EvaluationEvidenceBookGenerator()
    book = generator.build(**_inputs())

    first = generator.write(book, tmp_path / "first")
    second = generator.write(book, tmp_path / "second")

    assert [path.relative_to(tmp_path / "first") for path in first] == [
        path.relative_to(tmp_path / "second") for path in second
    ]
    for left, right in zip(first, second, strict=True):
        assert left.read_bytes() == right.read_bytes()
    payload = json.loads(first[0].read_text(encoding="utf-8"))
    assert payload["artifact_id"] == book.artifact_id
    assert len(payload["cases"]) == 2
    assert payload["cases"][1]["errors"]
    assert "Wilson score interval" in first[-1].read_text(encoding="utf-8")


def test_evidence_book_refuses_stale_source_commit() -> None:
    inputs = _inputs()
    inputs["current_commit"] = "new-head"

    with pytest.raises(ValueError, match="stale"):
        EvaluationEvidenceBookGenerator().build(**inputs)


def test_evidence_book_requires_exact_arithmetic_and_limitations() -> None:
    with pytest.raises(ValueError, match="arithmetic"):
        EvidenceBookAggregate(
            metric_id="retrieval.recall-at-5",
            definition_version=1,
            aggregation="macro-mean",
            population_unit="unique reviewed query",
            semantic_denominator="all unique reviewed queries",
            case_ids=("real-case-001", "real-case-002"),
            numerator=1.0,
            denominator=2.0,
            value=1.0,
            confidence_lower=0.0,
            confidence_upper=1.0,
            confidence_method="Wilson score interval",
            population_standard_deviation=0.5,
            worst_case_ids=("real-case-002",),
            baseline_value=None,
        )

    inputs = _inputs()
    inputs["limitations"] = ()
    with pytest.raises(ValueError, match="limitations"):
        EvaluationEvidenceBookGenerator().build(**inputs)


def test_evidence_book_forbids_conditional_failure_denominators() -> None:
    inputs = _inputs()
    aggregates = cast(tuple[EvidenceBookAggregate, ...], inputs["aggregates"])
    aggregate = aggregates[0]
    inputs["aggregates"] = (
        replace(
            aggregate,
            case_ids=("real-case-001",),
            worst_case_ids=("real-case-001",),
        ),
        aggregates[1],
    )

    with pytest.raises(ValueError, match="omits cases"):
        EvaluationEvidenceBookGenerator().build(**inputs)
