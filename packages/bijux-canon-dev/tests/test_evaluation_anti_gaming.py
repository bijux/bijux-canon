"""Tests for evaluation anti-gaming admission gates."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Callable

import pytest

from bijux_canon_dev.quality import (
    AntiGamingViolation,
    EvaluationAntiGamingGate,
    EvaluationSubmission,
    MetricPopulation,
    MetricTruthSource,
    SubmittedMetric,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SPLIT_PATH = REPO_ROOT / "examples/ancient-dna-research/truth/split.json"
TRUTH_ROOT = SPLIT_PATH.parent


def _submission() -> EvaluationSubmission:
    rows = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["cases"]
    questions = {
        row["question_id"]: row
        for row in (
            json.loads(line)
            for line in (TRUTH_ROOT / "research-questions.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
    }
    claims = [
        json.loads(line)
        for line in (TRUTH_ROOT / "claim-truth.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    case_ids = frozenset(str(row["case_id"]) for row in rows)
    query_ids = frozenset(str(row["question_id"]) for row in rows)
    claim_ids = frozenset(str(row["truth_id"]) for row in claims)
    hard = frozenset(
        str(row["case_id"])
        for row in rows
        if questions[row["question_id"]]["category"]
        in {"ambiguous", "conflict", "multi-hop", "out-of-scope"}
    )
    negative = frozenset(
        str(row["case_id"])
        for row in rows
        if questions[row["question_id"]]["abstention_expected"]
    )
    reviewed = case_ids
    metrics = (
        SubmittedMetric(
            metric_id="recall-at-5",
            numerator=18,
            denominator=len(query_ids),
            truth_source=MetricTruthSource.reviewed_question_evidence,
            population=MetricPopulation.query,
            sample_ids=query_ids,
        ),
        SubmittedMetric(
            metric_id="claim-faithfulness",
            numerator=31,
            denominator=len(claim_ids),
            truth_source=MetricTruthSource.reviewed_claim_relations,
            population=MetricPopulation.claim,
            sample_ids=claim_ids,
        ),
    )
    return EvaluationSubmission(
        source_commit="current-head",
        current_commit="current-head",
        evaluated_case_ids=case_ids,
        expected_case_ids=case_ids,
        hard_case_ids=hard,
        negative_case_ids=negative,
        reviewed_label_case_ids=reviewed,
        fixture_case_ids=frozenset(),
        real_case_ids=case_ids,
        skipped_case_ids=frozenset(),
        expected_sample_ids={
            MetricPopulation.query: query_ids,
            MetricPopulation.claim: claim_ids,
            MetricPopulation.evaluation_case: case_ids,
        },
        declared_denominators={item.metric_id: item.denominator for item in metrics},
        metrics=metrics,
        minimum_case_count=len(case_ids),
    )


def test_truth_submission_uses_semantic_metric_populations() -> None:
    submission = _submission()
    report = EvaluationAntiGamingGate().evaluate(submission)

    assert report.passed
    assert report.violations == ()
    assert submission.metrics[0].denominator == 18
    assert submission.metrics[1].denominator == 32
    assert len(submission.evaluated_case_ids) == 18


@pytest.mark.parametrize(
    ("mutation", "violation"),
    [
        (
            lambda item: replace(
                item,
                metrics=(
                    replace(
                        item.metrics[0],
                        truth_source=MetricTruthSource.evidence_presence,
                    ),
                    item.metrics[1],
                ),
            ),
            AntiGamingViolation.tautological_metric,
        ),
        (
            lambda item: replace(
                item,
                evaluated_case_ids=frozenset(tuple(item.evaluated_case_ids)[:10]),
            ),
            AntiGamingViolation.tiny_subset,
        ),
        (
            lambda item: replace(item, skipped_case_ids=item.hard_case_ids),
            AntiGamingViolation.skipped_hard_case,
        ),
        (
            lambda item: replace(
                item,
                fixture_case_ids=item.evaluated_case_ids,
                real_case_ids=frozenset(),
            ),
            AntiGamingViolation.fixture_only,
        ),
        (
            lambda item: replace(item, source_commit="stale-head"),
            AntiGamingViolation.stale_report,
        ),
        (
            lambda item: replace(
                item,
                declared_denominators={
                    **item.declared_denominators,
                    "recall-at-5": 40,
                },
            ),
            AntiGamingViolation.changed_denominator,
        ),
        (
            lambda item: replace(
                item,
                metrics=(
                    SubmittedMetric(
                        metric_id=item.metrics[0].metric_id,
                        numerator=len(item.evaluated_case_ids),
                        denominator=len(item.evaluated_case_ids),
                        truth_source=item.metrics[0].truth_source,
                        population=MetricPopulation.query,
                        sample_ids=item.evaluated_case_ids,
                    ),
                    item.metrics[1],
                ),
                declared_denominators={
                    **item.declared_denominators,
                    "recall-at-5": len(item.evaluated_case_ids),
                },
            ),
            AntiGamingViolation.wrong_semantic_population,
        ),
        (
            lambda item: replace(
                item,
                evaluated_case_ids=item.evaluated_case_ids - item.negative_case_ids,
            ),
            AntiGamingViolation.missing_negative_case,
        ),
        (
            lambda item: replace(
                item,
                reviewed_label_case_ids=frozenset(),
                metrics=(
                    replace(
                        item.metrics[0], truth_source=MetricTruthSource.system_output
                    ),
                    item.metrics[1],
                ),
            ),
            AntiGamingViolation.unreviewed_auto_label,
        ),
    ],
)
def test_each_gaming_shortcut_is_rejected(
    mutation: Callable[[EvaluationSubmission], EvaluationSubmission],
    violation: AntiGamingViolation,
) -> None:
    changed = mutation(_submission())

    report = EvaluationAntiGamingGate().evaluate(changed)

    assert not report.passed
    assert violation in report.violations


def test_metric_denominator_must_equal_unique_semantic_samples() -> None:
    with pytest.raises(ValueError, match="unique semantic samples"):
        SubmittedMetric(
            metric_id="recall-at-5",
            numerator=8,
            denominator=120,
            truth_source=MetricTruthSource.reviewed_qrels,
            population=MetricPopulation.query,
            sample_ids=frozenset(f"query-{index}" for index in range(8)),
        )
