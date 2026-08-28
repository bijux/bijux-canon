# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Identity-safe lexical, dense, and hybrid retrieval quality comparison."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from bijux_canon_index.evaluation.retrieval_metrics import (
    RetrievalEvaluationCase,
    RetrievalEvaluationReport,
    RetrievalMetricEvaluator,
    _sha256,
)


class RetrievalMode(StrEnum):
    """Retrieval modes required by the production comparison."""

    lexical = "lexical"
    dense = "dense"
    hybrid = "hybrid"


@dataclass(frozen=True, slots=True)
class RetrievalQualityPolicy:
    """Versioned minimum quality and cross-channel regression limits."""

    recall_at_5_minimum: float = 0.90
    mrr_at_10_minimum: float = 0.85
    ndcg_at_10_minimum: float = 0.85
    semantic_ndcg_gain_minimum: float = 0.05
    overall_ndcg_loss_maximum: float = 0.02

    def __post_init__(self) -> None:
        values = (
            self.recall_at_5_minimum,
            self.mrr_at_10_minimum,
            self.ndcg_at_10_minimum,
            self.semantic_ndcg_gain_minimum,
            self.overall_ndcg_loss_maximum,
        )
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("retrieval quality thresholds must lie within [0,1]")


@dataclass(frozen=True, slots=True)
class RetrievalQualityCheck:
    """One exact threshold observation in a retrieval comparison."""

    check_id: str
    subset: str
    operator: str
    threshold: float
    observed: float
    passed: bool


@dataclass(frozen=True, slots=True)
class RetrievalComparisonReport:
    """Complete same-input channel reports and quality conclusions."""

    schema_version: str
    lexical: RetrievalEvaluationReport
    dense: RetrievalEvaluationReport
    hybrid: RetrievalEvaluationReport
    semantic_query_ids: tuple[str, ...]
    checks: tuple[RetrievalQualityCheck, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.retrieval-comparison.v1":
            raise ValueError("retrieval comparison report schema is unsupported")
        expected = _comparison_identity(
            self.lexical,
            self.dense,
            self.hybrid,
            self.semantic_query_ids,
            self.checks,
        )
        if self.evidence_sha256 != expected:
            raise ValueError("retrieval comparison evidence identity mismatch")

    @property
    def passed(self) -> bool:
        """Return whether every declared retrieval quality requirement passed."""
        return all(check.passed for check in self.checks)


_DEFAULT_RETRIEVAL_QUALITY_POLICY = RetrievalQualityPolicy()


class RetrievalQualityComparator:
    """Compare identical channel inputs and enforce production thresholds."""

    def __init__(
        self, policy: RetrievalQualityPolicy = _DEFAULT_RETRIEVAL_QUALITY_POLICY
    ) -> None:
        self._policy = policy
        self._evaluator = RetrievalMetricEvaluator()

    def compare(
        self,
        *,
        lexical: tuple[RetrievalEvaluationCase, ...],
        dense: tuple[RetrievalEvaluationCase, ...],
        hybrid: tuple[RetrievalEvaluationCase, ...],
        semantic_query_ids: tuple[str, ...],
    ) -> RetrievalComparisonReport:
        """Compare three modes only when query, filter, and qrel identities match."""
        modes = {
            RetrievalMode.lexical: lexical,
            RetrievalMode.dense: dense,
            RetrievalMode.hybrid: hybrid,
        }
        query_ids = self._validate_same_inputs(modes)
        semantic_ids = self._validate_semantic_subset(
            query_ids,
            semantic_query_ids,
        )
        reports = {
            mode: self._evaluator.evaluate(cases) for mode, cases in modes.items()
        }
        semantic_reports = {
            mode: self._evaluator.evaluate(
                tuple(case for case in cases if case.query_id in semantic_ids)
            )
            for mode, cases in modes.items()
        }
        lexical_ndcg = reports[RetrievalMode.lexical].metric("ndcg-at-10").value
        dense_ndcg = reports[RetrievalMode.dense].metric("ndcg-at-10").value
        hybrid_report = reports[RetrievalMode.hybrid]
        hybrid_ndcg = hybrid_report.metric("ndcg-at-10").value
        semantic_best = max(
            semantic_reports[RetrievalMode.lexical].metric("ndcg-at-10").value,
            semantic_reports[RetrievalMode.dense].metric("ndcg-at-10").value,
        )
        semantic_hybrid = (
            semantic_reports[RetrievalMode.hybrid].metric("ndcg-at-10").value
        )
        semantic_gain = semantic_hybrid - semantic_best
        overall_loss = max(0.0, max(lexical_ndcg, dense_ndcg) - hybrid_ndcg)
        checks = (
            _minimum_check(
                "recall-at-5",
                "heldout-all",
                self._policy.recall_at_5_minimum,
                hybrid_report.metric("recall-at-5").value,
            ),
            _minimum_check(
                "mrr-at-10",
                "heldout-all",
                self._policy.mrr_at_10_minimum,
                hybrid_report.metric("mrr-at-10").value,
            ),
            _minimum_check(
                "ndcg-at-10",
                "heldout-all",
                self._policy.ndcg_at_10_minimum,
                hybrid_ndcg,
            ),
            _minimum_check(
                "hybrid-semantic-gain",
                "heldout-semantic-paraphrase",
                self._policy.semantic_ndcg_gain_minimum,
                semantic_gain,
            ),
            RetrievalQualityCheck(
                check_id="hybrid-overall-loss",
                subset="heldout-all",
                operator="lte",
                threshold=self._policy.overall_ndcg_loss_maximum,
                observed=overall_loss,
                passed=overall_loss <= self._policy.overall_ndcg_loss_maximum,
            ),
        )
        ordered_semantic_ids = tuple(sorted(semantic_ids))
        evidence_sha256 = _comparison_identity(
            reports[RetrievalMode.lexical],
            reports[RetrievalMode.dense],
            hybrid_report,
            ordered_semantic_ids,
            checks,
        )
        return RetrievalComparisonReport(
            schema_version="bijux.canon.index.retrieval-comparison.v1",
            lexical=reports[RetrievalMode.lexical],
            dense=reports[RetrievalMode.dense],
            hybrid=hybrid_report,
            semantic_query_ids=ordered_semantic_ids,
            checks=checks,
            evidence_sha256=evidence_sha256,
        )

    @staticmethod
    def _validate_same_inputs(
        modes: dict[RetrievalMode, tuple[RetrievalEvaluationCase, ...]],
    ) -> set[str]:
        keyed = {
            mode: {case.query_id: case for case in cases}
            for mode, cases in modes.items()
        }
        query_sets = {frozenset(cases) for cases in keyed.values()}
        if len(query_sets) != 1:
            raise ValueError("retrieval modes must evaluate identical query sets")
        query_ids = set(next(iter(query_sets)))
        if not query_ids:
            raise ValueError("retrieval comparison requires at least one query")
        for query_id in query_ids:
            references = tuple(keyed[mode][query_id] for mode in RetrievalMode)
            if len({case.input_identity_sha256 for case in references}) != 1:
                raise ValueError(
                    "retrieval modes must use identical query and filter identities"
                )
            if len({case.qrels for case in references}) != 1:
                raise ValueError("retrieval modes must use identical graded qrels")
        return query_ids

    @staticmethod
    def _validate_semantic_subset(
        query_ids: set[str],
        semantic_query_ids: tuple[str, ...],
    ) -> set[str]:
        semantic_ids = set(semantic_query_ids)
        if not semantic_ids:
            raise ValueError("semantic comparison subset must not be empty")
        if len(semantic_ids) != len(semantic_query_ids):
            raise ValueError("semantic comparison query identities must be unique")
        if not semantic_ids.issubset(query_ids):
            raise ValueError("semantic comparison references an unknown query")
        return semantic_ids


def _minimum_check(
    check_id: str,
    subset: str,
    threshold: float,
    observed: float,
) -> RetrievalQualityCheck:
    return RetrievalQualityCheck(
        check_id=check_id,
        subset=subset,
        operator="gte",
        threshold=threshold,
        observed=observed,
        passed=observed >= threshold,
    )


def _comparison_identity(
    lexical: RetrievalEvaluationReport,
    dense: RetrievalEvaluationReport,
    hybrid: RetrievalEvaluationReport,
    semantic_query_ids: tuple[str, ...],
    checks: tuple[RetrievalQualityCheck, ...],
) -> str:
    return _sha256(
        {
            "checks": [asdict(check) for check in checks],
            "dense_evidence_sha256": dense.evidence_sha256,
            "hybrid_evidence_sha256": hybrid.evidence_sha256,
            "lexical_evidence_sha256": lexical.evidence_sha256,
            "schema_version": "bijux.canon.index.retrieval-comparison.v1",
            "semantic_query_ids": semantic_query_ids,
        }
    )


__all__ = [
    "RetrievalComparisonReport",
    "RetrievalMode",
    "RetrievalQualityCheck",
    "RetrievalQualityComparator",
    "RetrievalQualityPolicy",
]
