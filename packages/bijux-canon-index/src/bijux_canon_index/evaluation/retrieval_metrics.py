# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Frozen qrel-based Recall, reciprocal-rank, and graded nDCG formulas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

_RECALL_CUTOFF = 5
_RANKING_CUTOFF = 10
_CONFIDENCE_LEVEL = 0.95
_NORMAL_95 = 1.959963984540054


class RetrievalEvaluationError(ValueError):
    """Retrieval inputs cannot produce an honest qrel-based metric report."""


@dataclass(frozen=True, slots=True)
class GradedQrel:
    """One independently reviewed relevance grade for an evidence identity."""

    evidence_id: str
    relevance_grade: int

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("qrel evidence identity must not be empty")
        if isinstance(self.relevance_grade, bool) or not 0 <= self.relevance_grade <= 3:
            raise ValueError(
                "qrel relevance grade must be an integer from zero to three"
            )


@dataclass(frozen=True, slots=True)
class RankedRetrievalHit:
    """One scored retrieval hit before deterministic metric ordering."""

    evidence_id: str
    score: float

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("retrieval hit evidence identity must not be empty")
        if isinstance(self.score, bool) or not math.isfinite(self.score):
            raise ValueError("retrieval hit score must be finite")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    """Frozen qrels and observed scored hits for one query."""

    query_id: str
    input_identity_sha256: str
    qrels: tuple[GradedQrel, ...]
    hits: tuple[RankedRetrievalHit, ...]

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("retrieval evaluation query identity must not be empty")
        if not _is_sha256(self.input_identity_sha256):
            raise ValueError("retrieval evaluation input identity must be a SHA-256")
        qrel_ids = tuple(qrel.evidence_id for qrel in self.qrels)
        hit_ids = tuple(hit.evidence_id for hit in self.hits)
        if len(qrel_ids) != len(set(qrel_ids)):
            raise ValueError("retrieval evaluation qrel identities must be unique")
        if len(hit_ids) != len(set(hit_ids)):
            raise ValueError("retrieval evaluation hit identities must be unique")
        if not any(qrel.relevance_grade > 0 for qrel in self.qrels):
            raise ValueError(
                "retrieval evaluation requires at least one positive qrel per query"
            )


@dataclass(frozen=True, slots=True)
class MetricConfidenceInterval:
    """Bounded confidence interval with its exact declared method."""

    level: float
    lower: float
    upper: float
    method: str

    def __post_init__(self) -> None:
        if not 0.0 < self.level < 1.0:
            raise ValueError("metric confidence level must be between zero and one")
        if not math.isfinite(self.lower) or not math.isfinite(self.upper):
            raise ValueError("metric confidence bounds must be finite")
        if not 0.0 <= self.lower <= self.upper <= 1.0:
            raise ValueError("metric confidence bounds must be ordered within [0,1]")
        if not self.method.strip():
            raise ValueError("metric confidence method must not be empty")


@dataclass(frozen=True, slots=True)
class QueryRetrievalMetrics:
    """Exact arithmetic and ranked evidence retained for one evaluated query."""

    query_id: str
    input_identity_sha256: str
    graded_qrels: tuple[GradedQrel, ...]
    ordered_hits: tuple[RankedRetrievalHit, ...]
    ordered_evidence_ids: tuple[str, ...]
    relevant_evidence_ids: tuple[str, ...]
    retrieved_relevant_at_5: tuple[str, ...]
    recall_at_5_numerator: int
    recall_at_5_denominator: int
    recall_at_5: float
    first_relevant_rank_at_10: int | None
    reciprocal_rank_at_10: float
    graded_gains_at_10: tuple[int, ...]
    ideal_graded_gains_at_10: tuple[int, ...]
    dcg_at_10: float
    ideal_dcg_at_10: float
    ndcg_at_10: float
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class AggregateRetrievalMetric:
    """Macro mean, arithmetic inputs, and interval for one frozen metric."""

    metric_id: str
    value: float
    numerator: float
    denominator: int
    formula: str
    samples: tuple[float, ...]
    confidence_interval: MetricConfidenceInterval

    def __post_init__(self) -> None:
        if self.denominator < 1 or self.denominator != len(self.samples):
            raise ValueError("macro metric denominator must equal its sample count")
        if not self.metric_id.strip() or not self.formula.strip():
            raise ValueError("macro metric identity and formula must not be empty")
        if any(not math.isfinite(sample) for sample in self.samples):
            raise ValueError("macro metric samples must be finite")
        if any(not 0.0 <= sample <= 1.0 for sample in self.samples):
            raise ValueError("macro metric samples must lie within [0,1]")
        if not math.isclose(self.numerator, math.fsum(self.samples)):
            raise ValueError("macro metric numerator does not match its samples")
        if not math.isclose(self.value, self.numerator / self.denominator):
            raise ValueError("macro metric value does not match its arithmetic")
        if not (
            self.confidence_interval.lower
            <= self.value
            <= self.confidence_interval.upper
        ):
            raise ValueError("macro metric value lies outside its confidence interval")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    """Complete per-query and macro retrieval metric evidence."""

    schema_version: str
    queries: tuple[QueryRetrievalMetrics, ...]
    metrics: tuple[AggregateRetrievalMetric, ...]
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.index.retrieval-evaluation.v1":
            raise ValueError("retrieval evaluation report schema is unsupported")
        query_ids = tuple(query.query_id for query in self.queries)
        metric_ids = tuple(metric.metric_id for metric in self.metrics)
        if not self.queries or len(query_ids) != len(set(query_ids)):
            raise ValueError(
                "retrieval evaluation report queries must be nonempty and unique"
            )
        if set(metric_ids) != {"recall-at-5", "mrr-at-10", "ndcg-at-10"}:
            raise ValueError("retrieval evaluation report metric set is incomplete")
        expected = _sha256(
            {
                "queries": [asdict(query) for query in self.queries],
                "metrics": [asdict(metric) for metric in self.metrics],
                "schema_version": self.schema_version,
            }
        )
        if self.evidence_sha256 != expected:
            raise ValueError("retrieval evaluation report evidence identity mismatch")

    def metric(self, metric_id: str) -> AggregateRetrievalMetric:
        """Return one named aggregate without relying on tuple position."""
        try:
            return next(
                metric for metric in self.metrics if metric.metric_id == metric_id
            )
        except StopIteration as exc:
            raise KeyError(f"retrieval metric not found: {metric_id}") from exc


class RetrievalMetricEvaluator:
    """Compute deterministic qrel metrics with explicit empty and tie policy."""

    def evaluate(
        self,
        cases: tuple[RetrievalEvaluationCase, ...],
    ) -> RetrievalEvaluationReport:
        """Evaluate unique queries and retain every macro sample."""
        if not cases:
            raise RetrievalEvaluationError(
                "retrieval evaluation requires at least one query"
            )
        query_ids = tuple(case.query_id for case in cases)
        if len(query_ids) != len(set(query_ids)):
            raise RetrievalEvaluationError(
                "retrieval evaluation query identities must be unique"
            )
        queries = tuple(self._evaluate_query(case) for case in cases)
        metrics = (
            self._aggregate(
                "recall-at-5",
                tuple(query.recall_at_5 for query in queries),
                "mean_q(|top_5(q) intersect relevant(q)| / |relevant(q)|)",
            ),
            self._aggregate(
                "mrr-at-10",
                tuple(query.reciprocal_rank_at_10 for query in queries),
                "mean_q(1 / first_relevant_rank_in_top_10(q), else 0)",
            ),
            self._aggregate(
                "ndcg-at-10",
                tuple(query.ndcg_at_10 for query in queries),
                "mean_q(DCG@10(q) / ideal_DCG@10(q)); gain=2^grade-1",
            ),
        )
        evidence_sha256 = _sha256(
            {
                "queries": [asdict(query) for query in queries],
                "metrics": [asdict(metric) for metric in metrics],
                "schema_version": "bijux.canon.index.retrieval-evaluation.v1",
            }
        )
        return RetrievalEvaluationReport(
            schema_version="bijux.canon.index.retrieval-evaluation.v1",
            queries=queries,
            metrics=metrics,
            evidence_sha256=evidence_sha256,
        )

    @staticmethod
    def _evaluate_query(case: RetrievalEvaluationCase) -> QueryRetrievalMetrics:
        ordered_hits = tuple(
            sorted(case.hits, key=lambda hit: (-hit.score, hit.evidence_id))
        )
        ordered_ids = tuple(hit.evidence_id for hit in ordered_hits)
        grades = {qrel.evidence_id: qrel.relevance_grade for qrel in case.qrels}
        relevant_ids = tuple(
            sorted(item for item, grade in grades.items() if grade > 0)
        )
        retrieved_at_5 = tuple(
            evidence_id
            for evidence_id in ordered_ids[:_RECALL_CUTOFF]
            if grades.get(evidence_id, 0) > 0
        )
        recall = len(retrieved_at_5) / len(relevant_ids)
        first_relevant = next(
            (
                rank
                for rank, evidence_id in enumerate(
                    ordered_ids[:_RANKING_CUTOFF],
                    start=1,
                )
                if grades.get(evidence_id, 0) > 0
            ),
            None,
        )
        reciprocal_rank = 0.0 if first_relevant is None else 1.0 / first_relevant
        gains = tuple(
            2 ** grades.get(evidence_id, 0) - 1
            for evidence_id in ordered_ids[:_RANKING_CUTOFF]
        )
        ideal_gains = tuple(
            sorted(
                (2**grade - 1 for grade in grades.values()),
                reverse=True,
            )[:_RANKING_CUTOFF]
        )
        dcg = _discounted_gain(gains)
        ideal_dcg = _discounted_gain(ideal_gains)
        ndcg = dcg / ideal_dcg
        arithmetic = {
            "dcg_at_10": dcg,
            "first_relevant_rank_at_10": first_relevant,
            "graded_qrels": [asdict(qrel) for qrel in case.qrels],
            "graded_gains_at_10": gains,
            "ideal_dcg_at_10": ideal_dcg,
            "ideal_graded_gains_at_10": ideal_gains,
            "input_identity_sha256": case.input_identity_sha256,
            "ndcg_at_10": ndcg,
            "ordered_evidence_ids": ordered_ids,
            "ordered_hits": [asdict(hit) for hit in ordered_hits],
            "query_id": case.query_id,
            "recall_at_5": recall,
            "recall_at_5_denominator": len(relevant_ids),
            "recall_at_5_numerator": len(retrieved_at_5),
            "reciprocal_rank_at_10": reciprocal_rank,
            "relevant_evidence_ids": relevant_ids,
            "retrieved_relevant_at_5": retrieved_at_5,
        }
        return QueryRetrievalMetrics(
            query_id=case.query_id,
            input_identity_sha256=case.input_identity_sha256,
            graded_qrels=case.qrels,
            ordered_hits=ordered_hits,
            ordered_evidence_ids=ordered_ids,
            relevant_evidence_ids=relevant_ids,
            retrieved_relevant_at_5=retrieved_at_5,
            recall_at_5_numerator=len(retrieved_at_5),
            recall_at_5_denominator=len(relevant_ids),
            recall_at_5=recall,
            first_relevant_rank_at_10=first_relevant,
            reciprocal_rank_at_10=reciprocal_rank,
            graded_gains_at_10=gains,
            ideal_graded_gains_at_10=ideal_gains,
            dcg_at_10=dcg,
            ideal_dcg_at_10=ideal_dcg,
            ndcg_at_10=ndcg,
            evidence_sha256=_sha256(arithmetic),
        )

    @staticmethod
    def _aggregate(
        metric_id: str,
        samples: tuple[float, ...],
        formula: str,
    ) -> AggregateRetrievalMetric:
        numerator = math.fsum(samples)
        value = numerator / len(samples)
        return AggregateRetrievalMetric(
            metric_id=metric_id,
            value=value,
            numerator=numerator,
            denominator=len(samples),
            formula=formula,
            samples=samples,
            confidence_interval=_confidence_interval(samples),
        )


def _discounted_gain(gains: tuple[int, ...]) -> float:
    return math.fsum(
        gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1)
    )


def _confidence_interval(samples: tuple[float, ...]) -> MetricConfidenceInterval:
    mean = math.fsum(samples) / len(samples)
    if len(samples) == 1:
        lower = upper = mean
    else:
        sample_variance = math.fsum((sample - mean) ** 2 for sample in samples) / (
            len(samples) - 1
        )
        margin = _NORMAL_95 * math.sqrt(sample_variance / len(samples))
        lower = max(0.0, mean - margin)
        upper = min(1.0, mean + margin)
    return MetricConfidenceInterval(
        level=_CONFIDENCE_LEVEL,
        lower=lower,
        upper=upper,
        method="two-sided normal approximation over per-query samples, clamped to [0,1]",
    )


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


__all__ = [
    "AggregateRetrievalMetric",
    "GradedQrel",
    "MetricConfidenceInterval",
    "QueryRetrievalMetrics",
    "RankedRetrievalHit",
    "RetrievalEvaluationCase",
    "RetrievalEvaluationError",
    "RetrievalEvaluationReport",
    "RetrievalMetricEvaluator",
]
