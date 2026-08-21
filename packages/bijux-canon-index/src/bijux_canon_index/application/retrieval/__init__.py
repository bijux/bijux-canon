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
from .lexical import (
    LexicalCandidateBatch,
    LexicalCandidateDecision,
    LexicalCandidateDisposition,
    LexicalCandidateOutcome,
    LexicalCandidateService,
)

__all__ = [
    "DenseCandidate",
    "DenseCandidateBatch",
    "DenseCandidateCompatibilityError",
    "DenseCandidateMode",
    "DenseCandidateOutcome",
    "DenseCandidateService",
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
    "RrfContribution",
    "RrfFusionBatch",
    "RrfFusionPolicy",
    "reciprocal_rank_fusion",
]
