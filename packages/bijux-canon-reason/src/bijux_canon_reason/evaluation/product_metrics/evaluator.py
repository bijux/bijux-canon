# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Unconditional aggregation over exact semantic case populations."""

from __future__ import annotations

import math

from bijux_canon_reason.evaluation.metrics import ConfidenceInterval, MetricDirection
from bijux_canon_reason.evaluation.product_metrics.catalog import (
    product_metric_catalog,
)
from bijux_canon_reason.evaluation.product_metrics.models import (
    ProductAnswerDisposition,
    ProductEvaluationCase,
    ProductExecutionStatus,
    ProductMetricAggregation,
    ProductMetricCaseOutcome,
    ProductMetricDefinition,
    ProductMetricMeasurement,
    ProductMetricReport,
    ProductMetricResult,
    _aggregate,
    _worst_case_ids,
)
from bijux_canon_reason.grounding.provider_contracts import content_artifact_id


class ProductMetricEvaluationError(ValueError):
    """The declared population or its metric arithmetic is incomplete."""


class UnconditionalProductMetricEvaluator:
    """Score all declared cases, including typed non-completions and partial labels."""

    def evaluate(
        self,
        *,
        cases: tuple[ProductEvaluationCase, ...],
        measurements: tuple[ProductMetricMeasurement, ...],
        source_identity_sha256: str,
        data_identity_sha256: str,
        model_identity_sha256: str,
        config_identity_sha256: str,
        metric_ids: tuple[str, ...] | None = None,
    ) -> ProductMetricReport:
        """Return content-bound metrics with exact population coverage."""

        if not cases:
            raise ProductMetricEvaluationError("product evaluation requires cases")
        case_ids = tuple(item.case_id for item in cases)
        if len(case_ids) != len(set(case_ids)):
            raise ProductMetricEvaluationError("product case IDs must be unique")
        definitions = _select_definitions(metric_ids)
        measurement_map = _index_measurements(measurements)
        expected_keys = {
            (definition.metric_id, case.case_id)
            for definition in definitions
            if definition.metric_id != "completion.product-success-rate"
            for case in cases
        }
        if set(measurement_map) != expected_keys:
            missing = sorted(expected_keys - set(measurement_map))
            unexpected = sorted(set(measurement_map) - expected_keys)
            raise ProductMetricEvaluationError(
                f"metric population is incomplete: missing={missing}, unexpected={unexpected}"
            )
        results = tuple(
            _result(
                definition,
                cases,
                measurement_map,
            )
            for definition in definitions
        )
        payload = {
            "schema_version": "bijux.canon.evaluation.product-metric-report.v1",
            "source_identity_sha256": source_identity_sha256,
            "data_identity_sha256": data_identity_sha256,
            "model_identity_sha256": model_identity_sha256,
            "config_identity_sha256": config_identity_sha256,
            "cases": tuple(item.model_dump(mode="json") for item in cases),
            "metrics": tuple(item.model_dump(mode="json") for item in results),
            "passed": all(item.passed for item in results),
        }
        return ProductMetricReport(
            artifact_id=content_artifact_id(payload),
            source_identity_sha256=source_identity_sha256,
            data_identity_sha256=data_identity_sha256,
            model_identity_sha256=model_identity_sha256,
            config_identity_sha256=config_identity_sha256,
            cases=cases,
            metrics=results,
            passed=all(item.passed for item in results),
        )


def _select_definitions(
    metric_ids: tuple[str, ...] | None,
) -> tuple[ProductMetricDefinition, ...]:
    catalog = {item.metric_id: item for item in product_metric_catalog()}
    selected_ids = tuple(catalog) if metric_ids is None else metric_ids
    if len(selected_ids) != len(set(selected_ids)):
        raise ProductMetricEvaluationError("selected metric IDs must be unique")
    unknown = sorted(set(selected_ids) - set(catalog))
    if unknown:
        raise ProductMetricEvaluationError(f"unknown product metrics: {unknown}")
    completion = "completion.product-success-rate"
    if completion not in selected_ids:
        selected_ids = (*selected_ids, completion)
    return tuple(catalog[metric_id] for metric_id in sorted(selected_ids))


def _index_measurements(
    measurements: tuple[ProductMetricMeasurement, ...],
) -> dict[tuple[str, str], ProductMetricMeasurement]:
    indexed = {(item.metric_id, item.case_id): item for item in measurements}
    if len(indexed) != len(measurements):
        raise ProductMetricEvaluationError(
            "metric measurements must be unique per metric and case"
        )
    return indexed


def _result(
    definition: ProductMetricDefinition,
    cases: tuple[ProductEvaluationCase, ...],
    measurements: dict[tuple[str, str], ProductMetricMeasurement],
) -> ProductMetricResult:
    outcomes = tuple(
        _outcome(
            definition, case, measurements.get((definition.metric_id, case.case_id))
        )
        for case in cases
    )
    numerator, denominator, value = _aggregate(definition, outcomes)
    values = tuple(item.value for item in outcomes)
    mean = sum(values) / len(values)
    deviation = math.sqrt(sum((item - mean) ** 2 for item in values) / len(values))
    interval = _confidence_interval(
        definition=definition,
        values=values,
        value=value,
        mean=mean,
        deviation=deviation,
        denominator=denominator,
    )
    status_counts = {
        status: sum(item.execution_status is status for item in outcomes)
        for status in ProductExecutionStatus
    }
    passed = (
        value >= definition.threshold
        if definition.direction is MetricDirection.higher_is_better
        else value <= definition.threshold
    )
    return ProductMetricResult(
        definition=definition,
        outcomes=outcomes,
        value=value,
        numerator=numerator,
        denominator=denominator,
        mean=mean,
        population_standard_deviation=deviation,
        confidence_interval=interval,
        worst_case_ids=_worst_case_ids(definition, outcomes),
        completed_cases=status_counts[ProductExecutionStatus.completed],
        refused_cases=status_counts[ProductExecutionStatus.refused],
        failed_cases=status_counts[ProductExecutionStatus.failed],
        cancelled_cases=status_counts[ProductExecutionStatus.cancelled],
        budget_exhausted_cases=status_counts[ProductExecutionStatus.budget_exhausted],
        fully_labeled_cases=sum(item.label_completeness == 1.0 for item in outcomes),
        partial_label_cases=sum(item.label_completeness < 1.0 for item in outcomes),
        passed=passed,
    )


def _outcome(
    definition: ProductMetricDefinition,
    case: ProductEvaluationCase,
    measurement: ProductMetricMeasurement | None,
) -> ProductMetricCaseOutcome:
    if definition.metric_id == "completion.product-success-rate":
        value = float(case.execution_status is ProductExecutionStatus.completed)
        return _case_outcome(case, numerator=value, denominator=1.0, value=value)
    assert measurement is not None
    numerator, denominator = _validated_arithmetic(definition, measurement)
    terminal_value = _terminal_value(definition, case.execution_status)
    if terminal_value is not None:
        if denominator == 0:
            denominator = 1.0
        numerator = terminal_value * denominator
        value = terminal_value
    elif denominator == 0:
        value = definition.empty_case_value
        if case.answer_disposition is ProductAnswerDisposition.answered:
            denominator = 1.0
            numerator = value
    else:
        value = numerator / denominator
    if value < definition.minimum_value or value > definition.maximum_value:
        raise ProductMetricEvaluationError(
            f"metric value outside definition: {definition.metric_id}/{case.case_id}"
        )
    return _case_outcome(
        case,
        numerator=numerator,
        denominator=denominator,
        value=value,
    )


def _validated_arithmetic(
    definition: ProductMetricDefinition,
    measurement: ProductMetricMeasurement,
) -> tuple[float, float]:
    numerator = measurement.numerator
    denominator = measurement.denominator
    if definition.aggregation in {
        ProductMetricAggregation.macro_mean,
        ProductMetricAggregation.micro_ratio,
    } and (numerator < 0 or numerator > denominator):
        raise ProductMetricEvaluationError(
            f"fraction arithmetic is invalid: {definition.metric_id}/{measurement.case_id}"
        )
    if (
        definition.aggregation
        in {
            ProductMetricAggregation.paired_mean_delta,
            ProductMetricAggregation.percentile_95,
        }
        and denominator != 1.0
    ):
        raise ProductMetricEvaluationError(
            f"scalar metric denominator must be one: {definition.metric_id}/{measurement.case_id}"
        )
    return numerator, denominator


def _terminal_value(
    definition: ProductMetricDefinition,
    status: ProductExecutionStatus,
) -> float | None:
    if status is ProductExecutionStatus.completed:
        return None
    if status is ProductExecutionStatus.refused:
        return definition.refused_case_value
    return definition.failed_case_value


def _confidence_interval(
    *,
    definition: ProductMetricDefinition,
    values: tuple[float, ...],
    value: float,
    mean: float,
    deviation: float,
    denominator: float,
) -> ConfidenceInterval:
    z = 1.959963984540054
    if definition.aggregation is ProductMetricAggregation.micro_ratio:
        if denominator == 0:
            lower, upper = definition.minimum_value, definition.maximum_value
        else:
            z_squared = z**2
            center = (value + z_squared / (2 * denominator)) / (
                1 + z_squared / denominator
            )
            margin = (
                z
                * math.sqrt(
                    value * (1 - value) / denominator + z_squared / (4 * denominator**2)
                )
                / (1 + z_squared / denominator)
            )
            lower, upper = center - margin, center + margin
    elif definition.aggregation is ProductMetricAggregation.percentile_95:
        ordered = sorted(values)
        center_rank = 0.95 * len(ordered)
        rank_margin = z * math.sqrt(len(ordered) * 0.95 * 0.05)
        lower_index = max(0, math.floor(center_rank - rank_margin) - 1)
        upper_index = min(len(ordered) - 1, math.ceil(center_rank + rank_margin) - 1)
        lower, upper = ordered[lower_index], ordered[upper_index]
    else:
        margin = z * deviation / math.sqrt(len(values))
        lower, upper = mean - margin, mean + margin
    lower = max(definition.minimum_value, min(lower, value))
    upper = min(definition.maximum_value, max(upper, value))
    return ConfidenceInterval(
        level=0.95,
        lower=lower,
        upper=upper,
        method=definition.uncertainty_method,
    )


def _case_outcome(
    case: ProductEvaluationCase,
    *,
    numerator: float,
    denominator: float,
    value: float,
) -> ProductMetricCaseOutcome:
    return ProductMetricCaseOutcome(
        case_id=case.case_id,
        execution_status=case.execution_status,
        answer_disposition=case.answer_disposition,
        failure_code=case.failure_code,
        label_completeness=case.label_completeness,
        numerator=numerator,
        denominator=denominator,
        value=value,
    )


__all__ = ["ProductMetricEvaluationError", "UnconditionalProductMetricEvaluator"]
