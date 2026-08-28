# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Unconditional, versioned product metric contracts."""

from __future__ import annotations

from bijux_canon_reason.evaluation.product_metrics.catalog import (
    product_metric_catalog,
)
from bijux_canon_reason.evaluation.product_metrics.evaluator import (
    ProductMetricEvaluationError,
    UnconditionalProductMetricEvaluator,
)
from bijux_canon_reason.evaluation.product_metrics.models import (
    ProductAnswerDisposition,
    ProductEvaluationCase,
    ProductExecutionStatus,
    ProductMetricAggregation,
    ProductMetricCaseOutcome,
    ProductMetricDefinition,
    ProductMetricDomain,
    ProductMetricMeasurement,
    ProductMetricReport,
    ProductMetricResult,
)

__all__ = [
    "ProductAnswerDisposition",
    "ProductEvaluationCase",
    "ProductExecutionStatus",
    "ProductMetricAggregation",
    "ProductMetricCaseOutcome",
    "ProductMetricDefinition",
    "ProductMetricDomain",
    "ProductMetricEvaluationError",
    "ProductMetricMeasurement",
    "ProductMetricReport",
    "ProductMetricResult",
    "UnconditionalProductMetricEvaluator",
    "product_metric_catalog",
]
