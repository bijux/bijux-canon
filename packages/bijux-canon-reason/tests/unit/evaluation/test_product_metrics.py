# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Hand-worked unconditional product metric contract checks."""

from __future__ import annotations

from copy import deepcopy

from pydantic import ValidationError
import pytest

from bijux_canon_reason.evaluation import (
    ProductAnswerDisposition,
    ProductEvaluationCase,
    ProductExecutionStatus,
    ProductMetricDomain,
    ProductMetricEvaluationError,
    ProductMetricMeasurement,
    ProductMetricReport,
    UnconditionalProductMetricEvaluator,
    product_metric_catalog,
)

_SELECTED = (
    "retrieval.recall-at-5",
    "citation.precision",
    "revision.expected-claim-recall-gain",
    "latency.warm-hybrid-operator-p95-ms",
)


def _cases() -> tuple[ProductEvaluationCase, ...]:
    return (
        ProductEvaluationCase(
            case_id="answered",
            execution_status=ProductExecutionStatus.completed,
            answer_disposition=ProductAnswerDisposition.answered,
            label_completeness=1.0,
        ),
        ProductEvaluationCase(
            case_id="refused",
            execution_status=ProductExecutionStatus.refused,
            answer_disposition=ProductAnswerDisposition.not_produced,
            failure_code="vex-witness-below-policy",
            label_completeness=1.0,
        ),
        ProductEvaluationCase(
            case_id="exhausted",
            execution_status=ProductExecutionStatus.budget_exhausted,
            answer_disposition=ProductAnswerDisposition.not_produced,
            failure_code="research-budget-exhausted",
            label_completeness=0.5,
        ),
    )


def _measurements() -> tuple[ProductMetricMeasurement, ...]:
    values = {
        "retrieval.recall-at-5": ((1.0, 1.0), (2.0, 2.0), (1.0, 2.0)),
        "citation.precision": ((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
        "revision.expected-claim-recall-gain": (
            (0.2, 1.0),
            (0.0, 1.0),
            (0.0, 1.0),
        ),
        "latency.warm-hybrid-operator-p95-ms": (
            (100.0, 1.0),
            (200.0, 1.0),
            (300.0, 1.0),
        ),
    }
    case_ids = tuple(item.case_id for item in _cases())
    return tuple(
        ProductMetricMeasurement(
            metric_id=metric_id,
            case_id=case_id,
            numerator=numerator,
            denominator=denominator,
        )
        for metric_id, arithmetic in values.items()
        for case_id, (numerator, denominator) in zip(case_ids, arithmetic, strict=True)
    )


def _report() -> ProductMetricReport:
    return UnconditionalProductMetricEvaluator().evaluate(
        cases=_cases(),
        measurements=_measurements(),
        source_identity_sha256="1" * 64,
        data_identity_sha256="2" * 64,
        model_identity_sha256="3" * 64,
        config_identity_sha256="4" * 64,
        metric_ids=_SELECTED,
    )


def test_catalog_defines_every_release_quality_domain() -> None:
    catalog = product_metric_catalog()

    assert tuple(item.metric_id for item in catalog) == tuple(
        sorted(item.metric_id for item in catalog)
    )
    assert {item.domain for item in catalog} == set(ProductMetricDomain)
    assert len({item.metric_id for item in catalog}) == len(catalog)
    assert all(item.definition_version == 1 for item in catalog)
    assert all(
        item.semantic_numerator and item.semantic_denominator for item in catalog
    )


def test_refusal_failure_empty_tie_and_partial_labels_remain_visible() -> None:
    report = _report()
    by_id = {item.definition.metric_id: item for item in report.metrics}

    retrieval = by_id["retrieval.recall-at-5"]
    assert retrieval.value == pytest.approx(1.0 / 3.0)
    assert retrieval.worst_case_ids == ("exhausted", "refused")
    assert retrieval.refused_cases == 1
    assert retrieval.budget_exhausted_cases == 1
    assert retrieval.partial_label_cases == 1

    citation = by_id["citation.precision"]
    assert citation.numerator == 0.0
    assert citation.denominator == 3.0
    assert citation.value == 0.0

    revision = by_id["revision.expected-claim-recall-gain"]
    assert revision.value == pytest.approx((0.2 - 1.0 - 1.0) / 3.0)
    assert revision.confidence_interval.lower == -1.0
    assert revision.confidence_interval.upper > revision.value

    latency = by_id["latency.warm-hybrid-operator-p95-ms"]
    assert latency.value == 300.0
    assert tuple(item.value for item in latency.outcomes) == (100.0, 200.0, 300.0)

    completion = by_id["completion.product-success-rate"]
    assert completion.numerator == 1.0
    assert completion.denominator == 3.0
    assert completion.value == pytest.approx(1.0 / 3.0)


def test_report_aggregates_can_be_independently_recomputed() -> None:
    report = _report()

    for metric in report.metrics:
        values = tuple(item.value for item in metric.outcomes)
        assert metric.mean == pytest.approx(sum(values) / len(values))
        assert {item.case_id for item in metric.outcomes} == {
            item.case_id for item in report.cases
        }
    restarted = ProductMetricReport.model_validate_json(report.model_dump_json())
    assert restarted == report

    tampered = deepcopy(report.model_dump(mode="json"))
    tampered["metrics"][0]["value"] += 0.1
    with pytest.raises(ValidationError, match="aggregate arithmetic"):
        ProductMetricReport.model_validate(tampered)


def test_duplicate_missing_and_unexpected_rows_are_rejected() -> None:
    evaluator = UnconditionalProductMetricEvaluator()
    measurements = _measurements()
    with pytest.raises(ProductMetricEvaluationError, match="unique per metric"):
        evaluator.evaluate(
            cases=_cases(),
            measurements=(*measurements, measurements[0]),
            source_identity_sha256="1" * 64,
            data_identity_sha256="2" * 64,
            model_identity_sha256="3" * 64,
            config_identity_sha256="4" * 64,
            metric_ids=_SELECTED,
        )
    with pytest.raises(ProductMetricEvaluationError, match="population is incomplete"):
        evaluator.evaluate(
            cases=_cases(),
            measurements=measurements[:-1],
            source_identity_sha256="1" * 64,
            data_identity_sha256="2" * 64,
            model_identity_sha256="3" * 64,
            config_identity_sha256="4" * 64,
            metric_ids=_SELECTED,
        )
    duplicate_cases = (*_cases(), _cases()[0])
    with pytest.raises(ProductMetricEvaluationError, match="case IDs must be unique"):
        evaluator.evaluate(
            cases=duplicate_cases,
            measurements=measurements,
            source_identity_sha256="1" * 64,
            data_identity_sha256="2" * 64,
            model_identity_sha256="3" * 64,
            config_identity_sha256="4" * 64,
            metric_ids=_SELECTED,
        )


def test_completed_abstention_is_terminal_success_not_refusal() -> None:
    case = ProductEvaluationCase(
        case_id="grounded-abstention",
        execution_status=ProductExecutionStatus.completed,
        answer_disposition=ProductAnswerDisposition.abstained,
        label_completeness=1.0,
    )
    report = UnconditionalProductMetricEvaluator().evaluate(
        cases=(case,),
        measurements=(
            ProductMetricMeasurement(
                metric_id="abstention.correctness",
                case_id=case.case_id,
                numerator=1.0,
                denominator=1.0,
            ),
        ),
        source_identity_sha256="1" * 64,
        data_identity_sha256="2" * 64,
        model_identity_sha256="3" * 64,
        config_identity_sha256="4" * 64,
        metric_ids=("abstention.correctness",),
    )
    by_id = {item.definition.metric_id: item for item in report.metrics}

    assert by_id["abstention.correctness"].value == 1.0
    assert by_id["completion.product-success-rate"].value == 1.0
