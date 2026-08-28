# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Auditable per-case outcomes and aggregate evaluation metric reports."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.truth import (
    EvaluationSplit,
    Identifier,
    NonEmptyText,
    Sha256,
)


class MetricDirection(StrEnum):
    """Direction in which a metric improves."""

    higher_is_better = "higher_is_better"
    lower_is_better = "lower_is_better"


class ConfidenceInterval(StableModel):
    """Confidence interval with an explicit statistical method."""

    level: float = Field(gt=0.0, lt=1.0)
    lower: float
    upper: float
    method: NonEmptyText

    @field_validator("lower", "upper")
    @classmethod
    def _require_finite_bound(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("confidence interval bounds must be finite")
        return value

    @model_validator(mode="after")
    def _validate_order(self) -> ConfidenceInterval:
        if self.lower > self.upper:
            raise ValueError("confidence interval lower bound exceeds upper bound")
        return self


class MetricObservation(StableModel):
    """Metric value with the exact arithmetic inputs used to compute it."""

    schema_version: Literal["bijux.canon.evaluation.metric-observation.v1"] = (
        "bijux.canon.evaluation.metric-observation.v1"
    )
    metric_id: Identifier
    metric_name: Identifier
    value: float
    numerator: float = Field(ge=0.0)
    denominator: float = Field(gt=0.0)
    formula: NonEmptyText
    direction: MetricDirection
    confidence_interval: ConfidenceInterval
    case_ids: tuple[Identifier, ...] = Field(min_length=1)
    raw_sample_uri: NonEmptyText

    @field_validator("value", "numerator", "denominator")
    @classmethod
    def _require_finite_value(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric arithmetic values must be finite")
        return value

    @model_validator(mode="after")
    def _require_unique_cases(self) -> MetricObservation:
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("metric case IDs must be unique")
        if (
            not self.confidence_interval.lower
            <= self.value
            <= self.confidence_interval.upper
        ):
            raise ValueError("metric value must lie within its confidence interval")
        return self


class EvaluationCaseOutcome(StableModel):
    """Reviewed outcome for one case and one system output."""

    schema_version: Literal["bijux.canon.evaluation.case-outcome.v1"] = (
        "bijux.canon.evaluation.case-outcome.v1"
    )
    case_id: Identifier
    system_output_id: Identifier
    reviewer_decision_ids: tuple[Identifier, ...] = Field(min_length=1)
    metric_ids: tuple[Identifier, ...] = Field(min_length=1)
    passed: bool
    failures: tuple[NonEmptyText, ...] = ()
    exclusions: tuple[NonEmptyText, ...] = ()

    @model_validator(mode="after")
    def _validate_outcome(self) -> EvaluationCaseOutcome:
        if len(set(self.reviewer_decision_ids)) != len(self.reviewer_decision_ids):
            raise ValueError("case outcome reviewer decision IDs must be unique")
        if len(set(self.metric_ids)) != len(self.metric_ids):
            raise ValueError("case outcome metric IDs must be unique")
        if self.passed and self.failures:
            raise ValueError("passing case outcomes cannot contain failures")
        return self


class EvaluationReport(StableModel):
    """Complete evaluation report with raw samples, identities, and limitations."""

    schema_version: Literal["bijux.canon.evaluation.report.v1"] = (
        "bijux.canon.evaluation.report.v1"
    )
    report_id: Identifier
    split: EvaluationSplit
    outcomes: tuple[EvaluationCaseOutcome, ...] = Field(min_length=1)
    metrics: tuple[MetricObservation, ...] = Field(min_length=1)
    raw_sample_uris: tuple[NonEmptyText, ...] = Field(min_length=1)
    failures: tuple[NonEmptyText, ...] = ()
    exclusions: tuple[NonEmptyText, ...] = ()
    source_identity_sha256: Sha256
    data_identity_sha256: Sha256
    model_identity_sha256: Sha256
    config_identity_sha256: Sha256
    limitations: tuple[NonEmptyText, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_report_references(self) -> EvaluationReport:
        case_ids = {outcome.case_id for outcome in self.outcomes}
        metric_ids = {metric.metric_id for metric in self.metrics}
        if len(case_ids) != len(self.outcomes):
            raise ValueError("evaluation report case IDs must be unique")
        if len(metric_ids) != len(self.metrics):
            raise ValueError("evaluation report metric IDs must be unique")
        referenced_metrics = {
            metric_id for outcome in self.outcomes for metric_id in outcome.metric_ids
        }
        if not referenced_metrics.issubset(metric_ids):
            raise ValueError("case outcome references an unknown report metric")
        observed_cases = {
            case_id for metric in self.metrics for case_id in metric.case_ids
        }
        if not observed_cases.issubset(case_ids):
            raise ValueError("metric observation references an unknown report case")
        declared_samples = set(self.raw_sample_uris)
        if any(
            metric.raw_sample_uri not in declared_samples for metric in self.metrics
        ):
            raise ValueError("metric raw sample is absent from the report index")
        return self


__all__ = [
    "ConfidenceInterval",
    "EvaluationCaseOutcome",
    "EvaluationReport",
    "MetricDirection",
    "MetricObservation",
]
