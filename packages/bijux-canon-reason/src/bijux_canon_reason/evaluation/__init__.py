# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Evaluation truth, output, review, metric, and suite contracts."""

from __future__ import annotations

from bijux_canon_reason.evaluation.metrics import (
    ConfidenceInterval,
    EvaluationCaseOutcome,
    EvaluationReport,
    MetricDirection,
    MetricObservation,
)
from bijux_canon_reason.evaluation.outcomes import (
    SystemAnswerDisposition,
    SystemCitation,
    SystemClaim,
    SystemClaimDisposition,
    SystemOutput,
)
from bijux_canon_reason.evaluation.reviews import (
    AdjudicationDecision,
    ReviewerDecision,
    ReviewSubjectKind,
    ReviewVerdict,
)
from bijux_canon_reason.evaluation.schema_catalog import (
    EVALUATION_SCHEMA_CATALOG_VERSION,
    evaluation_json_schemas,
    write_evaluation_json_schemas,
)
from bijux_canon_reason.evaluation.truth import (
    AbstentionExpectation,
    AtomicClaimTruth,
    CitationTruthLabel,
    CitationTruthRelation,
    ClaimTruthClass,
    ConflictExpectation,
    EvaluationCaseTruth,
    EvaluationQuery,
    EvaluationSplit,
    ExactEvidenceLocator,
    QrelJudgment,
    TruthProvenance,
)

__all__ = [
    "AbstentionExpectation",
    "AdjudicationDecision",
    "AtomicClaimTruth",
    "CitationTruthLabel",
    "CitationTruthRelation",
    "ClaimTruthClass",
    "ConfidenceInterval",
    "ConflictExpectation",
    "EVALUATION_SCHEMA_CATALOG_VERSION",
    "EvaluationCaseOutcome",
    "EvaluationCaseTruth",
    "EvaluationQuery",
    "EvaluationReport",
    "EvaluationSplit",
    "ExactEvidenceLocator",
    "MetricDirection",
    "MetricObservation",
    "QrelJudgment",
    "ReviewerDecision",
    "ReviewSubjectKind",
    "ReviewVerdict",
    "SystemAnswerDisposition",
    "SystemCitation",
    "SystemClaim",
    "SystemClaimDisposition",
    "SystemOutput",
    "TruthProvenance",
    "evaluation_json_schemas",
    "write_evaluation_json_schemas",
]
