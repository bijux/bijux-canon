"""Fail-closed checks for evaluation submissions and metric provenance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class MetricTruthSource(StrEnum):
    """Admissible and prohibited sources of evaluation credit."""

    reviewed_qrels = "reviewed-qrels"
    reviewed_claim_relations = "reviewed-claim-relations"
    evidence_presence = "evidence-presence"
    system_output = "system-output"


class MetricPopulation(StrEnum):
    """Semantic unit over which one submitted metric is aggregated."""

    query = "query"
    claim = "claim"
    evaluation_case = "evaluation-case"


class AntiGamingViolation(StrEnum):
    """Stable reasons an evaluation submission cannot be admitted."""

    tautological_metric = "tautological-metric"
    tiny_subset = "tiny-subset"
    skipped_hard_case = "skipped-hard-case"
    fixture_only = "fixture-only"
    stale_report = "stale-report"
    changed_denominator = "changed-denominator"
    wrong_semantic_population = "wrong-semantic-population"
    missing_negative_case = "missing-negative-case"
    unreviewed_auto_label = "unreviewed-auto-label"


@dataclass(frozen=True, slots=True)
class SubmittedMetric:
    """Exact arithmetic and truth provenance for one submitted metric."""

    metric_id: str
    numerator: int
    denominator: int
    truth_source: MetricTruthSource
    population: MetricPopulation
    sample_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.metric_id or self.denominator <= 0 or not self.sample_ids:
            raise ValueError("submitted metric identity and denominator are required")
        if not 0 <= self.numerator <= self.denominator:
            raise ValueError("submitted metric arithmetic is invalid")
        if self.denominator != len(self.sample_ids) or any(
            not sample_id for sample_id in self.sample_ids
        ):
            raise ValueError(
                "submitted metric denominator must equal unique semantic samples"
            )


@dataclass(frozen=True, slots=True)
class EvaluationSubmission:
    """Complete evaluation population, lineage, and declared denominators."""

    source_commit: str
    current_commit: str
    evaluated_case_ids: frozenset[str]
    expected_case_ids: frozenset[str]
    hard_case_ids: frozenset[str]
    negative_case_ids: frozenset[str]
    reviewed_label_case_ids: frozenset[str]
    fixture_case_ids: frozenset[str]
    real_case_ids: frozenset[str]
    skipped_case_ids: frozenset[str]
    expected_sample_ids: Mapping[MetricPopulation, frozenset[str]]
    declared_denominators: Mapping[str, int]
    metrics: tuple[SubmittedMetric, ...]
    minimum_case_count: int = 120

    def __post_init__(self) -> None:
        if self.minimum_case_count <= 0:
            raise ValueError("minimum evaluation case count must be positive")
        if not self.source_commit or not self.current_commit:
            raise ValueError("evaluation source and current commits are required")
        if len({item.metric_id for item in self.metrics}) != len(self.metrics):
            raise ValueError("submitted metric IDs must be unique")
        object.__setattr__(
            self,
            "declared_denominators",
            MappingProxyType(dict(self.declared_denominators)),
        )
        object.__setattr__(
            self,
            "expected_sample_ids",
            MappingProxyType(
                {
                    population: frozenset(sample_ids)
                    for population, sample_ids in self.expected_sample_ids.items()
                }
            ),
        )
        if set(self.expected_sample_ids) != set(MetricPopulation):
            raise ValueError("every metric semantic population must be declared")
        if any(not sample_ids for sample_ids in self.expected_sample_ids.values()):
            raise ValueError("metric semantic populations must not be empty")


@dataclass(frozen=True, slots=True)
class AntiGamingGateReport:
    """Every detected gaming condition without early-exit hiding."""

    violations: tuple[AntiGamingViolation, ...]
    passed: bool

    def __post_init__(self) -> None:
        if len(set(self.violations)) != len(self.violations):
            raise ValueError("anti-gaming violations must be unique")
        if self.passed != (not self.violations):
            raise ValueError("anti-gaming gate status is inconsistent")


class EvaluationAntiGamingGate:
    """Reject gaming shortcuts before evaluation evidence is published."""

    def evaluate(self, submission: EvaluationSubmission) -> AntiGamingGateReport:
        """Evaluate all anti-gaming rules and retain every violation."""
        violations: list[AntiGamingViolation] = []
        metric_sources = {item.truth_source for item in submission.metrics}
        if metric_sources.intersection(
            {MetricTruthSource.evidence_presence, MetricTruthSource.system_output}
        ):
            violations.append(AntiGamingViolation.tautological_metric)
        if (
            len(submission.evaluated_case_ids) < submission.minimum_case_count
            or submission.evaluated_case_ids != submission.expected_case_ids
        ):
            violations.append(AntiGamingViolation.tiny_subset)
        if not submission.hard_case_ids.issubset(
            submission.evaluated_case_ids
        ) or submission.hard_case_ids.intersection(submission.skipped_case_ids):
            violations.append(AntiGamingViolation.skipped_hard_case)
        if submission.evaluated_case_ids and (
            submission.evaluated_case_ids.issubset(submission.fixture_case_ids)
            or not submission.evaluated_case_ids.intersection(submission.real_case_ids)
        ):
            violations.append(AntiGamingViolation.fixture_only)
        if submission.source_commit != submission.current_commit:
            violations.append(AntiGamingViolation.stale_report)
        if any(
            submission.declared_denominators.get(item.metric_id) != item.denominator
            for item in submission.metrics
        ):
            violations.append(AntiGamingViolation.changed_denominator)
        if any(
            item.sample_ids != submission.expected_sample_ids[item.population]
            for item in submission.metrics
        ):
            violations.append(AntiGamingViolation.wrong_semantic_population)
        if not submission.negative_case_ids.issubset(submission.evaluated_case_ids):
            violations.append(AntiGamingViolation.missing_negative_case)
        if (
            not submission.evaluated_case_ids.issubset(
                submission.reviewed_label_case_ids
            )
            or MetricTruthSource.system_output in metric_sources
        ):
            violations.append(AntiGamingViolation.unreviewed_auto_label)
        ordered = tuple(item for item in AntiGamingViolation if item in set(violations))
        return AntiGamingGateReport(violations=ordered, passed=not ordered)


__all__ = [
    "AntiGamingGateReport",
    "AntiGamingViolation",
    "EvaluationAntiGamingGate",
    "EvaluationSubmission",
    "MetricPopulation",
    "MetricTruthSource",
    "SubmittedMetric",
]
