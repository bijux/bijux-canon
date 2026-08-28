# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Versioned product metric definitions and unconditional case evidence."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.metrics import ConfidenceInterval, MetricDirection
from bijux_canon_reason.evaluation.truth import Identifier, NonEmptyText, Sha256
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class ProductMetricDomain(StrEnum):
    """Stable product boundary measured by a metric."""

    retrieval = "retrieval"
    ann = "ann"
    claim = "claim"
    citation = "citation"
    abstention = "abstention"
    conflict = "conflict"
    counterevidence = "counterevidence"
    revision = "revision"
    unsupported_rate = "unsupported-rate"
    latency = "latency"
    completion = "completion"


class ProductExecutionStatus(StrEnum):
    """Terminal execution status retained in every applicable metric sample."""

    completed = "completed"
    refused = "refused"
    failed = "failed"
    cancelled = "cancelled"
    budget_exhausted = "budget-exhausted"


class ProductAnswerDisposition(StrEnum):
    """Semantic answer outcome, separate from execution completion."""

    answered = "answered"
    partially_abstained = "partially-abstained"
    abstained = "abstained"
    insufficient = "insufficient"
    not_produced = "not-produced"


class ProductMetricAggregation(StrEnum):
    """Allowed aggregation, chosen according to the semantic population unit."""

    macro_mean = "macro-mean"
    micro_ratio = "micro-ratio"
    percentile_95 = "percentile-95"
    paired_mean_delta = "paired-mean-delta"


class ProductMetricDefinition(StableModel):
    """Immutable definition of one product quality number."""

    schema_version: Literal["bijux.canon.evaluation.metric-definition.v1"] = (
        "bijux.canon.evaluation.metric-definition.v1"
    )
    metric_id: Identifier
    domain: ProductMetricDomain
    definition_version: Literal[1] = 1
    direction: MetricDirection
    aggregation: ProductMetricAggregation
    population_unit: NonEmptyText
    semantic_numerator: NonEmptyText
    semantic_denominator: NonEmptyText
    empty_case_value: float
    refused_case_value: float | None
    failed_case_value: float | None
    threshold: float
    minimum_value: float
    maximum_value: float
    uncertainty_method: NonEmptyText

    @field_validator(
        "empty_case_value",
        "refused_case_value",
        "failed_case_value",
        "threshold",
        "minimum_value",
        "maximum_value",
    )
    @classmethod
    def _require_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("metric definition values must be finite")
        return value

    @model_validator(mode="after")
    def _validate_bounds(self) -> Self:
        if self.minimum_value > self.maximum_value:
            raise ValueError("metric definition bounds are reversed")
        bounded = (
            self.empty_case_value,
            self.threshold,
            *(() if self.refused_case_value is None else (self.refused_case_value,)),
            *(() if self.failed_case_value is None else (self.failed_case_value,)),
        )
        if any(
            value < self.minimum_value or value > self.maximum_value
            for value in bounded
        ):
            raise ValueError("metric policy value falls outside its declared bounds")
        if self.aggregation is ProductMetricAggregation.percentile_95 and (
            self.refused_case_value is not None or self.failed_case_value is not None
        ):
            raise ValueError(
                "latency percentiles must retain observed terminal latency"
            )
        return self


class ProductEvaluationCase(StableModel):
    """One unique semantic case in the unconditional product population."""

    schema_version: Literal["bijux.canon.evaluation.product-case.v1"] = (
        "bijux.canon.evaluation.product-case.v1"
    )
    case_id: Identifier
    execution_status: ProductExecutionStatus
    answer_disposition: ProductAnswerDisposition
    failure_code: NonEmptyText | None = None
    label_completeness: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_terminal_outcome(self) -> Self:
        incomplete = self.execution_status is not ProductExecutionStatus.completed
        if incomplete != (self.failure_code is not None):
            raise ValueError(
                "non-completed cases require exactly one typed failure code"
            )
        if (
            incomplete
            and self.answer_disposition is not ProductAnswerDisposition.not_produced
        ):
            raise ValueError("non-completed cases cannot claim an answer disposition")
        if (
            not incomplete
            and self.answer_disposition is ProductAnswerDisposition.not_produced
        ):
            raise ValueError("completed cases require a semantic answer disposition")
        return self


class ProductMetricMeasurement(StableModel):
    """Raw reviewed arithmetic for one metric and one population case."""

    schema_version: Literal["bijux.canon.evaluation.metric-measurement.v1"] = (
        "bijux.canon.evaluation.metric-measurement.v1"
    )
    metric_id: Identifier
    case_id: Identifier
    numerator: float
    denominator: float = Field(ge=0.0)

    @field_validator("numerator", "denominator")
    @classmethod
    def _require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric measurement arithmetic must be finite")
        return value


class ProductMetricCaseOutcome(StableModel):
    """Scored per-case value with terminal and labeling status preserved."""

    case_id: Identifier
    execution_status: ProductExecutionStatus
    answer_disposition: ProductAnswerDisposition
    failure_code: NonEmptyText | None
    label_completeness: float = Field(ge=0.0, le=1.0)
    numerator: float
    denominator: float = Field(ge=0.0)
    value: float

    @field_validator("numerator", "denominator", "value")
    @classmethod
    def _require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric case values must be finite")
        return value


class ProductMetricResult(StableModel):
    """Recomputable aggregate, dispersion, uncertainty, and worst cases."""

    definition: ProductMetricDefinition
    outcomes: tuple[ProductMetricCaseOutcome, ...] = Field(min_length=1)
    value: float
    numerator: float
    denominator: float = Field(ge=0.0)
    mean: float
    population_standard_deviation: float = Field(ge=0.0)
    confidence_interval: ConfidenceInterval
    worst_case_ids: tuple[Identifier, ...] = Field(min_length=1)
    completed_cases: int = Field(ge=0)
    refused_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    cancelled_cases: int = Field(ge=0)
    budget_exhausted_cases: int = Field(ge=0)
    fully_labeled_cases: int = Field(ge=0)
    partial_label_cases: int = Field(ge=0)
    passed: bool

    @field_validator("value", "numerator", "denominator", "mean")
    @classmethod
    def _require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("product metric aggregates must be finite")
        return value

    @model_validator(mode="after")
    def _validate_recomputable_result(self) -> Self:
        case_ids = tuple(item.case_id for item in self.outcomes)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("product metric outcome case IDs must be unique")
        if any(
            item.value < self.definition.minimum_value
            or item.value > self.definition.maximum_value
            for item in self.outcomes
        ):
            raise ValueError("product metric case value falls outside definition")
        for item in self.outcomes:
            terminal_value = _terminal_policy_value(
                self.definition, item.execution_status
            )
            if terminal_value is not None:
                if (
                    item.denominator <= 0
                    or not math.isclose(
                        item.numerator,
                        terminal_value * item.denominator,
                        abs_tol=1e-12,
                    )
                    or not math.isclose(item.value, terminal_value, abs_tol=1e-12)
                ):
                    raise ValueError(
                        "terminal metric case does not follow the definition policy"
                    )
            else:
                expected_case_value = (
                    self.definition.empty_case_value
                    if item.denominator == 0
                    else item.numerator / item.denominator
                )
                if not math.isclose(item.value, expected_case_value, abs_tol=1e-12):
                    raise ValueError("product metric case arithmetic is inconsistent")
        values = tuple(item.value for item in self.outcomes)
        expected_mean = sum(values) / len(values)
        expected_deviation = math.sqrt(
            sum((value - expected_mean) ** 2 for value in values) / len(values)
        )
        if not math.isclose(self.mean, expected_mean, abs_tol=1e-12):
            raise ValueError("product metric mean is not recomputable")
        if not math.isclose(
            self.population_standard_deviation,
            expected_deviation,
            abs_tol=1e-12,
        ):
            raise ValueError("product metric dispersion is not recomputable")
        expected_numerator, expected_denominator, expected_value = _aggregate(
            self.definition, self.outcomes
        )
        if not all(
            math.isclose(observed, expected, abs_tol=1e-12)
            for observed, expected in (
                (self.numerator, expected_numerator),
                (self.denominator, expected_denominator),
                (self.value, expected_value),
            )
        ):
            raise ValueError("product metric aggregate arithmetic is inconsistent")
        expected_worst = _worst_case_ids(self.definition, self.outcomes)
        if self.worst_case_ids != expected_worst:
            raise ValueError("product metric worst cases are inconsistent")
        status_counts = {
            status: sum(item.execution_status is status for item in self.outcomes)
            for status in ProductExecutionStatus
        }
        observed_counts = {
            ProductExecutionStatus.completed: self.completed_cases,
            ProductExecutionStatus.refused: self.refused_cases,
            ProductExecutionStatus.failed: self.failed_cases,
            ProductExecutionStatus.cancelled: self.cancelled_cases,
            ProductExecutionStatus.budget_exhausted: self.budget_exhausted_cases,
        }
        if status_counts != observed_counts:
            raise ValueError("product metric terminal status counts are inconsistent")
        full = sum(item.label_completeness == 1.0 for item in self.outcomes)
        if self.fully_labeled_cases != full:
            raise ValueError("fully labeled case count is inconsistent")
        if self.partial_label_cases != len(self.outcomes) - full:
            raise ValueError("partial label case count is inconsistent")
        if not (
            self.confidence_interval.lower
            <= self.value
            <= self.confidence_interval.upper
        ):
            raise ValueError("product metric confidence interval excludes its value")
        expected_passed = (
            self.value >= self.definition.threshold
            if self.definition.direction is MetricDirection.higher_is_better
            else self.value <= self.definition.threshold
        )
        if self.passed != expected_passed:
            raise ValueError("product metric threshold status is inconsistent")
        return self


class ProductMetricReport(StableModel):
    """Content-bound unconditional metrics over one exact case population."""

    schema_version: Literal["bijux.canon.evaluation.product-metric-report.v1"] = (
        "bijux.canon.evaluation.product-metric-report.v1"
    )
    artifact_id: NonEmptyText
    source_identity_sha256: Sha256
    data_identity_sha256: Sha256
    model_identity_sha256: Sha256
    config_identity_sha256: Sha256
    cases: tuple[ProductEvaluationCase, ...] = Field(min_length=1)
    metrics: tuple[ProductMetricResult, ...] = Field(min_length=1)
    passed: bool

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_population(self) -> Self:
        case_ids = tuple(item.case_id for item in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("product metric case IDs must be unique")
        metric_ids = tuple(item.definition.metric_id for item in self.metrics)
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("product metric definitions must be unique")
        expected_cases = set(case_ids)
        for metric in self.metrics:
            observed = tuple(item.case_id for item in metric.outcomes)
            if len(observed) != len(set(observed)) or set(observed) != expected_cases:
                raise ValueError(
                    "every product metric must retain the exact declared case population"
                )
        if "completion.product-success-rate" not in metric_ids:
            raise ValueError("product report requires unconditional completion")
        if self.passed != all(item.passed for item in self.metrics):
            raise ValueError("product metric report status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("product metric report identity does not match")
        return self


def _aggregate(
    definition: ProductMetricDefinition,
    outcomes: tuple[ProductMetricCaseOutcome, ...],
) -> tuple[float, float, float]:
    if definition.aggregation is ProductMetricAggregation.micro_ratio:
        numerator = sum(item.numerator for item in outcomes)
        denominator = sum(item.denominator for item in outcomes)
        value = (
            definition.empty_case_value if denominator == 0 else numerator / denominator
        )
        return numerator, denominator, value
    values = tuple(item.value for item in outcomes)
    if definition.aggregation is ProductMetricAggregation.percentile_95:
        ordered = sorted(values)
        value = ordered[math.ceil(0.95 * len(ordered)) - 1]
        return value, 1.0, value
    numerator = sum(values)
    denominator = float(len(values))
    return numerator, denominator, numerator / denominator


def _terminal_policy_value(
    definition: ProductMetricDefinition,
    status: ProductExecutionStatus,
) -> float | None:
    if status is ProductExecutionStatus.completed:
        return None
    if status is ProductExecutionStatus.refused:
        return definition.refused_case_value
    return definition.failed_case_value


def _worst_case_ids(
    definition: ProductMetricDefinition,
    outcomes: tuple[ProductMetricCaseOutcome, ...],
) -> tuple[Identifier, ...]:
    reverse = definition.direction is MetricDirection.lower_is_better
    ordered = sorted(
        outcomes, key=lambda item: (item.value, item.case_id), reverse=reverse
    )
    worst_value = ordered[0].value
    return tuple(sorted(item.case_id for item in ordered if item.value == worst_value))


__all__ = [
    "ProductAnswerDisposition",
    "ProductEvaluationCase",
    "ProductExecutionStatus",
    "ProductMetricAggregation",
    "ProductMetricCaseOutcome",
    "ProductMetricDefinition",
    "ProductMetricDomain",
    "ProductMetricMeasurement",
    "ProductMetricReport",
    "ProductMetricResult",
]
