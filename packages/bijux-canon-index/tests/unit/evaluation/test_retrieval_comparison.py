# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for same-input lexical, dense, and hybrid quality comparison."""

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_index.evaluation import (
    GradedQrel,
    RankedRetrievalHit,
    RetrievalEvaluationCase,
    RetrievalQualityComparator,
)


def _case(
    query_id: str,
    *,
    hit: bool,
    identity: str = "a" * 64,
) -> RetrievalEvaluationCase:
    return RetrievalEvaluationCase(
        query_id=query_id,
        input_identity_sha256=identity,
        qrels=(GradedQrel(f"{query_id}-relevant", 3),),
        hits=((RankedRetrievalHit(f"{query_id}-relevant", 1.0),) if hit else ()),
    )


def test_hybrid_comparison_enforces_all_declared_quality_requirements() -> None:
    lexical = (_case("literal", hit=True), _case("semantic", hit=False))
    dense = (_case("literal", hit=True), _case("semantic", hit=False))
    hybrid = (_case("literal", hit=True), _case("semantic", hit=True))

    report = RetrievalQualityComparator().compare(
        lexical=lexical,
        dense=dense,
        hybrid=hybrid,
        semantic_query_ids=("semantic",),
    )

    assert report.passed
    assert report.semantic_query_ids == ("semantic",)
    assert tuple(check.check_id for check in report.checks) == (
        "recall-at-5",
        "mrr-at-10",
        "ndcg-at-10",
        "hybrid-semantic-gain",
        "hybrid-overall-loss",
    )
    observations = {check.check_id: check.observed for check in report.checks}
    assert observations["recall-at-5"] == 1.0
    assert observations["mrr-at-10"] == 1.0
    assert observations["ndcg-at-10"] == 1.0
    assert observations["hybrid-semantic-gain"] == 1.0
    assert observations["hybrid-overall-loss"] == 0.0
    assert (
        report.evidence_sha256
        == RetrievalQualityComparator()
        .compare(
            lexical=lexical,
            dense=dense,
            hybrid=hybrid,
            semantic_query_ids=("semantic",),
        )
        .evidence_sha256
    )


def test_quality_failures_remain_visible_instead_of_changing_denominators() -> None:
    lexical = (_case("literal", hit=True), _case("semantic", hit=True))
    dense = lexical
    hybrid = (_case("literal", hit=False), _case("semantic", hit=False))

    report = RetrievalQualityComparator().compare(
        lexical=lexical,
        dense=dense,
        hybrid=hybrid,
        semantic_query_ids=("semantic",),
    )

    assert not report.passed
    failed = {check.check_id for check in report.checks if not check.passed}
    assert failed == {
        "recall-at-5",
        "mrr-at-10",
        "ndcg-at-10",
        "hybrid-semantic-gain",
        "hybrid-overall-loss",
    }
    assert report.hybrid.metric("recall-at-5").denominator == 2
    assert report.hybrid.metric("recall-at-5").samples == (0.0, 0.0)


def test_comparison_rejects_mismatched_inputs_qrels_and_subsets() -> None:
    reference = (_case("query", hit=True),)
    changed_identity = (_case("query", hit=True, identity="b" * 64),)

    with pytest.raises(ValueError, match="query and filter identities"):
        RetrievalQualityComparator().compare(
            lexical=reference,
            dense=changed_identity,
            hybrid=reference,
            semantic_query_ids=("query",),
        )

    changed_qrels = (replace(reference[0], qrels=(GradedQrel("another-evidence", 3),)),)
    with pytest.raises(ValueError, match="identical graded qrels"):
        RetrievalQualityComparator().compare(
            lexical=reference,
            dense=changed_qrels,
            hybrid=reference,
            semantic_query_ids=("query",),
        )

    with pytest.raises(ValueError, match="unknown query"):
        RetrievalQualityComparator().compare(
            lexical=reference,
            dense=reference,
            hybrid=reference,
            semantic_query_ids=("missing",),
        )
