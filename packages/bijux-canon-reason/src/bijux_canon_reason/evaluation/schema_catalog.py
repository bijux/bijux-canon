# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Deterministic JSON Schema catalog for evaluation records."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

from pydantic import BaseModel

from bijux_canon_reason.evaluation.claim_matching import (
    ClaimMatchAdjudication,
    ClaimMatchReport,
    ClaimMatchReview,
)
from bijux_canon_reason.evaluation.metrics import (
    EvaluationCaseOutcome,
    EvaluationReport,
    MetricObservation,
)
from bijux_canon_reason.evaluation.outcomes import SystemOutput
from bijux_canon_reason.evaluation.product_metrics import (
    ProductEvaluationCase,
    ProductMetricDefinition,
    ProductMetricMeasurement,
    ProductMetricReport,
)
from bijux_canon_reason.evaluation.reviews import (
    AdjudicationDecision,
    ReviewerDecision,
)
from bijux_canon_reason.evaluation.truth import (
    AtomicClaimTruth,
    CitationTruthLabel,
    EvaluationCaseTruth,
    EvaluationQuery,
    QrelJudgment,
)

EVALUATION_SCHEMA_CATALOG_VERSION = "bijux.canon.evaluation.schema-catalog.v3"

_SCHEMA_MODELS: Mapping[str, type[BaseModel]] = {
    "adjudication": AdjudicationDecision,
    "atomic-claim-truth": AtomicClaimTruth,
    "case-outcome": EvaluationCaseOutcome,
    "case-truth": EvaluationCaseTruth,
    "claim-match-adjudication": ClaimMatchAdjudication,
    "claim-match-report": ClaimMatchReport,
    "claim-match-review": ClaimMatchReview,
    "citation-truth": CitationTruthLabel,
    "metric-observation": MetricObservation,
    "product-case": ProductEvaluationCase,
    "product-metric-definition": ProductMetricDefinition,
    "product-metric-measurement": ProductMetricMeasurement,
    "product-metric-report": ProductMetricReport,
    "qrel": QrelJudgment,
    "query": EvaluationQuery,
    "report": EvaluationReport,
    "reviewer-decision": ReviewerDecision,
    "system-output": SystemOutput,
}


def evaluation_json_schemas() -> dict[str, dict[str, object]]:
    """Return stable JSON Schemas for every externally persisted record."""

    schemas: dict[str, dict[str, object]] = {}
    for name, model in _SCHEMA_MODELS.items():
        schema = model.model_json_schema(mode="serialization")
        schema["$id"] = f"https://bijux.io/schemas/evaluation/{name}-v1.json"
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schemas[name] = schema
    return schemas


def write_evaluation_json_schemas(output_directory: Path) -> tuple[Path, ...]:
    """Write the catalog as deterministic, standalone JSON Schema documents."""

    if output_directory.is_symlink():
        raise ValueError("evaluation schema output directory cannot be a symlink")
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in evaluation_json_schemas().items():
        path = output_directory / f"{name}.schema.json"
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return tuple(written)


__all__ = [
    "EVALUATION_SCHEMA_CATALOG_VERSION",
    "evaluation_json_schemas",
    "write_evaluation_json_schemas",
]
