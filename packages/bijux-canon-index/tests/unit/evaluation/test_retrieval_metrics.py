# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for exact qrel-based retrieval evaluation formulas."""

from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import pytest

from bijux_canon_index.evaluation import (
    GradedQrel,
    RankedRetrievalHit,
    RetrievalEvaluationCase,
    RetrievalEvaluationError,
    RetrievalMetricEvaluator,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
QRELS_PATH = REPO_ROOT / "examples/ancient-dna-research/truth/qrels.jsonl"


def _case(
    query_id: str,
    *,
    hits: tuple[RankedRetrievalHit, ...],
) -> RetrievalEvaluationCase:
    return RetrievalEvaluationCase(
        query_id=query_id,
        qrels=(
            GradedQrel("evidence-a", 3),
            GradedQrel("evidence-b", 2),
            GradedQrel("evidence-c", 1),
            GradedQrel("evidence-negative", 0),
        ),
        hits=hits,
    )


def test_per_query_metrics_retain_exact_arithmetic_and_stable_ties() -> None:
    case = _case(
        "query-1",
        hits=(
            RankedRetrievalHit("evidence-z", 0.5),
            RankedRetrievalHit("evidence-b", 0.9),
            RankedRetrievalHit("evidence-a", 0.5),
            RankedRetrievalHit("evidence-c", 0.1),
        ),
    )

    report = RetrievalMetricEvaluator().evaluate((case,))
    query = report.queries[0]

    assert query.ordered_evidence_ids == (
        "evidence-b",
        "evidence-a",
        "evidence-z",
        "evidence-c",
    )
    assert query.retrieved_relevant_at_5 == (
        "evidence-b",
        "evidence-a",
        "evidence-c",
    )
    assert query.recall_at_5_numerator == 3
    assert query.recall_at_5_denominator == 3
    assert query.recall_at_5 == 1.0
    assert query.first_relevant_rank_at_10 == 1
    assert query.reciprocal_rank_at_10 == 1.0
    expected_dcg = 3 / math.log2(2) + 7 / math.log2(3) + 1 / math.log2(5)
    expected_ideal = 7 / math.log2(2) + 3 / math.log2(3) + 1 / math.log2(4)
    assert query.dcg_at_10 == pytest.approx(expected_dcg)
    assert query.ideal_dcg_at_10 == pytest.approx(expected_ideal)
    assert query.ndcg_at_10 == pytest.approx(expected_dcg / expected_ideal)
    assert len(query.evidence_sha256) == 64


def test_empty_results_score_zero_without_changing_denominators() -> None:
    report = RetrievalMetricEvaluator().evaluate((_case("query-empty", hits=()),))
    query = report.queries[0]

    assert query.ordered_evidence_ids == ()
    assert query.recall_at_5 == 0.0
    assert query.recall_at_5_denominator == 3
    assert query.first_relevant_rank_at_10 is None
    assert query.reciprocal_rank_at_10 == 0.0
    assert query.ndcg_at_10 == 0.0
    assert report.metric("recall-at-5").confidence_interval.lower == 0.0
    assert report.metric("recall-at-5").confidence_interval.upper == 0.0


def test_macro_metrics_retain_samples_and_bounded_confidence_intervals() -> None:
    perfect = _case(
        "query-perfect",
        hits=(
            RankedRetrievalHit("evidence-a", 3.0),
            RankedRetrievalHit("evidence-b", 2.0),
            RankedRetrievalHit("evidence-c", 1.0),
        ),
    )
    empty = _case("query-empty", hits=())

    report = RetrievalMetricEvaluator().evaluate((perfect, empty))

    for metric_id in ("recall-at-5", "mrr-at-10", "ndcg-at-10"):
        metric = report.metric(metric_id)
        assert metric.denominator == 2
        assert metric.samples == (1.0, 0.0)
        assert metric.numerator == 1.0
        assert metric.value == 0.5
        assert metric.confidence_interval.level == 0.95
        assert 0.0 <= metric.confidence_interval.lower <= metric.value
        assert metric.value <= metric.confidence_interval.upper <= 1.0
    assert (
        report.evidence_sha256
        == RetrievalMetricEvaluator().evaluate((perfect, empty)).evidence_sha256
    )


def test_invalid_denominators_duplicates_and_nonfinite_scores_fail_closed() -> None:
    with pytest.raises(ValueError, match="positive qrel"):
        RetrievalEvaluationCase(
            query_id="no-positive-truth",
            qrels=(GradedQrel("negative", 0),),
            hits=(),
        )
    with pytest.raises(ValueError, match="hit identities must be unique"):
        _case(
            "duplicate-hits",
            hits=(
                RankedRetrievalHit("same", 1.0),
                RankedRetrievalHit("same", 0.5),
            ),
        )
    with pytest.raises(ValueError, match="finite"):
        RankedRetrievalHit("evidence", float("nan"))
    with pytest.raises(RetrievalEvaluationError, match="at least one query"):
        RetrievalMetricEvaluator().evaluate(())

    report = RetrievalMetricEvaluator().evaluate((_case("tamper", hits=()),))
    with pytest.raises(ValueError, match="evidence identity mismatch"):
        replace(report, evidence_sha256="0" * 64)


def test_reviewed_ancient_dna_qrels_produce_per_query_evidence() -> None:
    records = [
        json.loads(line) for line in QRELS_PATH.read_text(encoding="utf-8").splitlines()
    ]
    query_id = str(records[0]["query_id"])
    selected = [record for record in records if record["query_id"] == query_id]
    case = RetrievalEvaluationCase(
        query_id=query_id,
        qrels=tuple(
            GradedQrel(
                evidence_id=str(record["chunk"]["chunk_id"]),
                relevance_grade=int(record["relevance_grade"]),
            )
            for record in selected
        ),
        hits=tuple(
            RankedRetrievalHit(
                evidence_id=str(record["chunk"]["chunk_id"]),
                score=float(record["relevance_grade"]),
            )
            for record in selected
        ),
    )

    report = RetrievalMetricEvaluator().evaluate((case,))

    assert report.queries[0].query_id == query_id
    assert report.metric("recall-at-5").value == 1.0
    assert report.metric("mrr-at-10").value == 1.0
    assert report.metric("ndcg-at-10").value == 1.0
