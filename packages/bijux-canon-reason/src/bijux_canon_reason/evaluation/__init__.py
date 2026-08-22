# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Evaluation truth, output, review, metric, and suite contracts."""

from __future__ import annotations

from bijux_canon_reason.evaluation.annotation import (
    AnnotationAdjudication,
    AnnotationAdjudicationVerdict,
    AnnotationAdmission,
    AnnotationConflict,
    AnnotationProtocol,
    AnnotationReview,
    AnnotationReviewVerdict,
    AnnotationRevision,
    AnnotationWorkflowError,
    IndependentAnnotationWorkflow,
)
from bijux_canon_reason.evaluation.citation_metrics import (
    CitationIntegrityEvaluationError,
    CitationIntegrityEvaluator,
    CitationIntegrityFailure,
    CitationIntegrityFailureCode,
    CitationIntegrityOutcome,
    CitationIntegrityOwner,
    CitationIntegrityReport,
)
from bijux_canon_reason.evaluation.citation_quality import (
    CitationQualityEvaluationError,
    CitationQualityEvaluator,
    CitationQualityFailure,
    CitationQualityFailureCode,
    CitationQualityMetric,
    CitationQualityReport,
)
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
    "AnnotationAdjudication",
    "AnnotationAdjudicationVerdict",
    "AnnotationAdmission",
    "AnnotationConflict",
    "AnnotationProtocol",
    "AnnotationReview",
    "AnnotationReviewVerdict",
    "AnnotationRevision",
    "AnnotationWorkflowError",
    "AdjudicationDecision",
    "AtomicClaimTruth",
    "CitationTruthLabel",
    "CitationTruthRelation",
    "CitationIntegrityEvaluationError",
    "CitationIntegrityEvaluator",
    "CitationIntegrityFailure",
    "CitationIntegrityFailureCode",
    "CitationIntegrityOutcome",
    "CitationIntegrityOwner",
    "CitationIntegrityReport",
    "CitationQualityEvaluationError",
    "CitationQualityEvaluator",
    "CitationQualityFailure",
    "CitationQualityFailureCode",
    "CitationQualityMetric",
    "CitationQualityReport",
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
    "IndependentAnnotationWorkflow",
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
