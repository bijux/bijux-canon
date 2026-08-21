# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical retrieval application services."""

from .dense import (
    DenseCandidate,
    DenseCandidateBatch,
    DenseCandidateCompatibilityError,
    DenseCandidateMode,
    DenseCandidateOutcome,
    DenseCandidateService,
    QueryEmbeddingProvider,
)
from .fusion import (
    FusedCandidate,
    FusionChannelRanking,
    RankedChannelCandidate,
    RetrievalChannel,
    RrfContribution,
    RrfFusionBatch,
    RrfFusionPolicy,
    reciprocal_rank_fusion,
)
from .filters import RetrievalFilterCapability, retrieval_filter_capability
from .lexical import (
    LexicalCandidateBatch,
    LexicalCandidateDecision,
    LexicalCandidateDisposition,
    LexicalCandidateOutcome,
    LexicalCandidateService,
)
from .selection import (
    DeduplicationKey,
    EvidenceDeduplicationPolicy,
    EvidenceDiversityPolicy,
    EvidenceLineage,
    EvidenceSelectionBatch,
    EvidenceSelectionDecision,
    EvidenceSelectionDisposition,
    EvidenceSelectionPolicy,
    select_evidence,
)
from .reranking import (
    RerankBatch,
    RerankFailurePolicy,
    RerankOutcome,
    RerankPolicy,
    RerankResponse,
    RerankScore,
    RerankedCandidate,
    Reranker,
    rerank_candidates,
)

__all__ = [
    "DeduplicationKey",
    "DenseCandidate",
    "DenseCandidateBatch",
    "DenseCandidateCompatibilityError",
    "DenseCandidateMode",
    "DenseCandidateOutcome",
    "DenseCandidateService",
    "EvidenceDeduplicationPolicy",
    "EvidenceDiversityPolicy",
    "EvidenceLineage",
    "EvidenceSelectionBatch",
    "EvidenceSelectionDecision",
    "EvidenceSelectionDisposition",
    "EvidenceSelectionPolicy",
    "FusedCandidate",
    "FusionChannelRanking",
    "LexicalCandidateBatch",
    "LexicalCandidateDecision",
    "LexicalCandidateDisposition",
    "LexicalCandidateOutcome",
    "LexicalCandidateService",
    "QueryEmbeddingProvider",
    "RankedChannelCandidate",
    "RetrievalChannel",
    "RetrievalFilterCapability",
    "RerankBatch",
    "RerankFailurePolicy",
    "RerankOutcome",
    "RerankPolicy",
    "RerankResponse",
    "RerankScore",
    "RerankedCandidate",
    "Reranker",
    "RrfContribution",
    "RrfFusionBatch",
    "RrfFusionPolicy",
    "reciprocal_rank_fusion",
    "retrieval_filter_capability",
    "rerank_candidates",
    "select_evidence",
]
