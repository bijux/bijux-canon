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
    MetricTruthSource,
    SubmittedMetric,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SPLIT_PATH = REPO_ROOT / "examples/ancient-dna-research/truth/split.json"


def _submission() -> EvaluationSubmission:
    rows = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["cases"]
    case_ids = frozenset(str(row["case_id"]) for row in rows)
    hard = frozenset(
        str(row["case_id"])
        for row in rows
        if row["difficulty"] in {"hard", "adversarial"}
    )
    negative = frozenset(
        str(row["case_id"]) for row in rows if row["labels"]["negative"]
    )
    reviewed = frozenset(
        str(row["case_id"])
        for row in rows
        if str(row["review_status"]).endswith("manual_review_complete")
    )
    metrics = (
        SubmittedMetric(
            metric_id="recall-at-5",
            numerator=114,
            denominator=len(case_ids),
            truth_source=MetricTruthSource.reviewed_qrels,
        ),
        SubmittedMetric(
            metric_id="claim-faithfulness",
            numerator=116,
            denominator=len(case_ids),
            truth_source=MetricTruthSource.reviewed_claim_relations,
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
        declared_denominators={item.metric_id: len(case_ids) for item in metrics},
        metrics=metrics,
    )


def test_real_120_case_submission_passes_all_anti_gaming_rules() -> None:
    report = EvaluationAntiGamingGate().evaluate(_submission())

    assert report.passed
    assert report.violations == ()


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
