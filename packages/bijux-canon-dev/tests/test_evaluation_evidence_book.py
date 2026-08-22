"""Tests for deterministic evaluation evidence-book generation."""

from __future__ import annotations

import json

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
                metrics={"recall-at-5": 1.0},
            ),
            EvidenceBookCaseResult(
                case_id="real-case-002",
                passed=False,
                metrics={"recall-at-5": 0.0},
                errors=("expected qrel was not retrieved",),
            ),
        ),
        "aggregates": (
            EvidenceBookAggregate(
                metric_id="recall-at-5",
                numerator=1.0,
                denominator=2.0,
                value=0.5,
                confidence_lower=0.1,
                confidence_upper=0.9,
                confidence_method="Wilson score interval",
                baseline_value=0.4,
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
            metric_id="recall-at-5",
            numerator=1.0,
            denominator=2.0,
            value=1.0,
            confidence_lower=0.0,
            confidence_upper=1.0,
            confidence_method="Wilson score interval",
            baseline_value=None,
        )

    inputs = _inputs()
    inputs["limitations"] = ()
    with pytest.raises(ValueError, match="limitations"):
        EvaluationEvidenceBookGenerator().build(**inputs)
