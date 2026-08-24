# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Authoritative catalog for product quality metric semantics."""

from __future__ import annotations

from bijux_canon_reason.evaluation.metrics import MetricDirection
from bijux_canon_reason.evaluation.product_metrics.models import (
    ProductMetricAggregation,
    ProductMetricDefinition,
    ProductMetricDomain,
)


def product_metric_catalog() -> tuple[ProductMetricDefinition, ...]:
    """Return every release metric definition in deterministic identity order."""

    ratio_uncertainty = (
        "deterministic 95% interval appropriate to the declared aggregation"
    )
    return tuple(
        sorted(
            (
                _fraction(
                    "retrieval.recall-at-5",
                    ProductMetricDomain.retrieval,
                    ProductMetricAggregation.macro_mean,
                    "unique reviewed query",
                    "reviewed relevant qrels retrieved in the first five final hits",
                    "all reviewed relevant qrels for the query",
                    0.90,
                    ratio_uncertainty,
                ),
                _fraction(
                    "retrieval.reciprocal-rank-at-10",
                    ProductMetricDomain.retrieval,
                    ProductMetricAggregation.macro_mean,
                    "unique reviewed query",
                    "reciprocal rank of the first relevant final hit at depth ten",
                    "one unique reviewed query",
                    0.85,
                    ratio_uncertainty,
                ),
                _fraction(
                    "retrieval.ndcg-at-10",
                    ProductMetricDomain.retrieval,
                    ProductMetricAggregation.macro_mean,
                    "unique reviewed query",
                    "discounted graded gain in the first ten final hits",
                    "ideal discounted graded gain for the same query",
                    0.85,
                    ratio_uncertainty,
                ),
                _fraction(
                    "ann.exact-witness-recall-at-10",
                    ProductMetricDomain.ann,
                    ProductMetricAggregation.macro_mean,
                    "unique reviewed dense query",
                    "exact-witness top-ten neighbors present in the ANN top ten",
                    "exact-witness top-ten neighbors",
                    0.95,
                    ratio_uncertainty,
                ),
                _fraction(
                    "claim.expected-recall",
                    ProductMetricDomain.claim,
                    ProductMetricAggregation.micro_ratio,
                    "independently reviewed expected atomic claim",
                    "reviewed expected claims correctly emitted",
                    "all reviewed expected claims across every case",
                    0.90,
                    ratio_uncertainty,
                ),
                _fraction(
                    "claim.supported-coverage",
                    ProductMetricDomain.claim,
                    ProductMetricAggregation.micro_ratio,
                    "emitted atomic claim",
                    "emitted claims directly supported by verified citations",
                    "all emitted claims, with failed outputs charged by reviewed expectations",
                    0.95,
                    ratio_uncertainty,
                ),
                _fraction(
                    "citation.precision",
                    ProductMetricDomain.citation,
                    ProductMetricAggregation.micro_ratio,
                    "emitted claim-to-citation relation",
                    "emitted citation relations independently judged supporting",
                    "all emitted citation relations, with empty invalid answers scoring zero",
                    0.95,
                    ratio_uncertainty,
                ),
                _fraction(
                    "citation.recall",
                    ProductMetricDomain.citation,
                    ProductMetricAggregation.micro_ratio,
                    "reviewed expected claim-to-evidence relation",
                    "reviewed expected citation relations correctly emitted",
                    "all reviewed expected citation relations",
                    0.90,
                    ratio_uncertainty,
                ),
                _fraction(
                    "abstention.correctness",
                    ProductMetricDomain.abstention,
                    ProductMetricAggregation.macro_mean,
                    "unique reviewed answerability case",
                    "one when answer or abstention matches reviewed answerability, else zero",
                    "one unique reviewed answerability case",
                    0.90,
                    ratio_uncertainty,
                ),
                _fraction(
                    "conflict.retention",
                    ProductMetricDomain.conflict,
                    ProductMetricAggregation.micro_ratio,
                    "reviewed conflict or qualification",
                    "reviewed conflicts and qualifications retained in graph and answer",
                    "all reviewed conflicts and qualifications",
                    1.0,
                    ratio_uncertainty,
                ),
                _lower_fraction(
                    "conflict.false-consensus-rate",
                    ProductMetricDomain.conflict,
                    "reviewed conflict",
                    "reviewed conflicts incorrectly presented as consensus",
                    "all reviewed conflicts",
                    0.0,
                    ratio_uncertainty,
                ),
                _fraction(
                    "counterevidence.recall",
                    ProductMetricDomain.counterevidence,
                    ProductMetricAggregation.micro_ratio,
                    "reviewed material counterevidence relation",
                    "reviewed material counterevidence found and classified",
                    "all reviewed material counterevidence relations",
                    0.90,
                    ratio_uncertainty,
                ),
                ProductMetricDefinition(
                    metric_id="revision.expected-claim-recall-gain",
                    domain=ProductMetricDomain.revision,
                    direction=MetricDirection.higher_is_better,
                    aggregation=ProductMetricAggregation.paired_mean_delta,
                    population_unit="paired unique RAG/RAR question",
                    semantic_numerator=(
                        "RAR expected-claim recall minus paired RAG expected-claim recall"
                    ),
                    semantic_denominator="one paired unique reviewed question",
                    empty_case_value=-1.0,
                    refused_case_value=-1.0,
                    failed_case_value=-1.0,
                    threshold=0.05,
                    minimum_value=-1.0,
                    maximum_value=1.0,
                    uncertainty_method=(
                        "normal-approximation 95% interval over paired recall deltas"
                    ),
                ),
                _lower_fraction(
                    "unsupported-claim.rate",
                    ProductMetricDomain.unsupported_rate,
                    "emitted or reviewed-expected atomic claim",
                    "emitted unsupported claims plus expected claims lost to terminal failure",
                    "all emitted claims, or reviewed expected claims when no output exists",
                    0.05,
                    ratio_uncertainty,
                ),
                _latency(
                    "latency.warm-hybrid-engine-p95-ms",
                    "measured engine milliseconds for one warm hybrid query",
                ),
                _latency(
                    "latency.warm-hybrid-operator-p95-ms",
                    "measured end-to-end operator milliseconds for one warm hybrid query",
                ),
                _fraction(
                    "completion.product-success-rate",
                    ProductMetricDomain.completion,
                    ProductMetricAggregation.macro_mean,
                    "unique attempted product case",
                    "cases reaching a typed completed result, including grounded abstention",
                    "all attempted cases including refusals, failures, cancellation, and budget exhaustion",
                    1.0,
                    ratio_uncertainty,
                ),
            ),
            key=lambda item: item.metric_id,
        )
    )


def _fraction(
    metric_id: str,
    domain: ProductMetricDomain,
    aggregation: ProductMetricAggregation,
    population_unit: str,
    numerator: str,
    denominator: str,
    threshold: float,
    uncertainty: str,
) -> ProductMetricDefinition:
    return ProductMetricDefinition(
        metric_id=metric_id,
        domain=domain,
        direction=MetricDirection.higher_is_better,
        aggregation=aggregation,
        population_unit=population_unit,
        semantic_numerator=numerator,
        semantic_denominator=denominator,
        empty_case_value=0.0,
        refused_case_value=0.0,
        failed_case_value=0.0,
        threshold=threshold,
        minimum_value=0.0,
        maximum_value=1.0,
        uncertainty_method=uncertainty,
    )


def _lower_fraction(
    metric_id: str,
    domain: ProductMetricDomain,
    population_unit: str,
    numerator: str,
    denominator: str,
    threshold: float,
    uncertainty: str,
) -> ProductMetricDefinition:
    return ProductMetricDefinition(
        metric_id=metric_id,
        domain=domain,
        direction=MetricDirection.lower_is_better,
        aggregation=ProductMetricAggregation.micro_ratio,
        population_unit=population_unit,
        semantic_numerator=numerator,
        semantic_denominator=denominator,
        empty_case_value=0.0,
        refused_case_value=1.0,
        failed_case_value=1.0,
        threshold=threshold,
        minimum_value=0.0,
        maximum_value=1.0,
        uncertainty_method=uncertainty,
    )


def _latency(metric_id: str, numerator: str) -> ProductMetricDefinition:
    return ProductMetricDefinition(
        metric_id=metric_id,
        domain=ProductMetricDomain.latency,
        direction=MetricDirection.lower_is_better,
        aggregation=ProductMetricAggregation.percentile_95,
        population_unit="unique attempted warm hybrid query",
        semantic_numerator=numerator,
        semantic_denominator="one attempted query regardless of terminal status",
        empty_case_value=0.0,
        refused_case_value=None,
        failed_case_value=None,
        threshold=750.0,
        minimum_value=0.0,
        maximum_value=86_400_000.0,
        uncertainty_method=(
            "distribution-free approximate 95% order-statistic interval over all attempts"
        ),
    )


__all__ = ["product_metric_catalog"]
