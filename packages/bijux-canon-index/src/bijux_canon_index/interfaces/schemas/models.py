# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Models schemas for interface payloads."""

from __future__ import annotations

from bijux_canon_index.interfaces.schemas.base import StrictModel
from bijux_canon_index.interfaces.schemas.reports import (
    BackendCapabilitiesReport,
    StorageBackendDescriptor,
    VectorStoreDescriptor,
)
from bijux_canon_index.interfaces.schemas.requests import (
    CreateRequest,
    ExecutionArtifactRequest,
    ExecutionBudgetPayload,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
    RandomnessProfilePayload,
)
from bijux_canon_index.interfaces.schemas.index_generations import (
    HnswParametersPayload,
    IndexActivationRequestPayload,
    IndexBuildLimitsPayload,
    IndexBuildRequestPayload,
    IndexChunkPayload,
    IndexInspectionResponse,
    IndexQueryRequestPayload,
    IndexQueryResponse,
    IndexSelectionPayload,
    MetadataFilterPayload,
    UserMetadataPredicatePayload,
)

__all__ = [
    "BackendCapabilitiesReport",
    "CreateRequest",
    "HnswParametersPayload",
    "IndexActivationRequestPayload",
    "IndexBuildLimitsPayload",
    "IndexBuildRequestPayload",
    "IndexChunkPayload",
    "IndexInspectionResponse",
    "IndexQueryRequestPayload",
    "IndexQueryResponse",
    "IndexSelectionPayload",
    "ExecutionArtifactRequest",
    "ExecutionBudgetPayload",
    "ExecutionRequestPayload",
    "ExplainRequest",
    "IngestRequest",
    "MetadataFilterPayload",
    "RandomnessProfilePayload",
    "StorageBackendDescriptor",
    "StrictModel",
    "VectorStoreDescriptor",
    "UserMetadataPredicatePayload",
]
