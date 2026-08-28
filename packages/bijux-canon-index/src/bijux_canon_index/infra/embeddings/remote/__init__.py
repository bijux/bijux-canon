# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Optional remote embedding boundary."""

from .client import RemoteEmbeddingClient
from .contracts import (
    EndpointClass,
    FailureCategory,
    RemoteEmbeddingBatch,
    RemoteEmbeddingConfig,
    RemoteEmbeddingError,
    RemoteEmbeddingProvenance,
    RemoteEmbeddingTransport,
    RemoteEmbeddingUsage,
    RemoteHTTPResponse,
    RemoteTimeouts,
)
from .transport import StandardLibraryEmbeddingTransport

__all__ = [
    "EndpointClass",
    "FailureCategory",
    "RemoteEmbeddingBatch",
    "RemoteEmbeddingClient",
    "RemoteEmbeddingConfig",
    "RemoteEmbeddingError",
    "RemoteEmbeddingProvenance",
    "RemoteEmbeddingTransport",
    "RemoteEmbeddingUsage",
    "RemoteHTTPResponse",
    "RemoteTimeouts",
    "StandardLibraryEmbeddingTransport",
]
