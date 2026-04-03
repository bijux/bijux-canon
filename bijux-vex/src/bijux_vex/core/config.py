# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class VectorStoreConfig:
    backend: str | None = None
    uri: str | None = None
    options: Mapping[str, str] | None = None


@dataclass(frozen=True)
class EmbeddingCacheConfig:
    backend: str | None = None
    uri: str | None = None
    options: Mapping[str, str] | None = None


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str | None = None
    model: str | None = None
    cache: EmbeddingCacheConfig | None = None


@dataclass(frozen=True)
class ExecutionConfig:
    vector_store: VectorStoreConfig | None = None
    embeddings: EmbeddingConfig | None = None
    resource_limits: ResourceLimits | None = None


@dataclass(frozen=True)
class ResourceLimits:
    max_vectors_per_ingest: int | None = None
    max_k: int | None = None
    max_query_size: int | None = None
    max_execution_time_ms: int | None = None


__all__ = [
    "VectorStoreConfig",
    "EmbeddingCacheConfig",
    "EmbeddingConfig",
    "ExecutionConfig",
    "ResourceLimits",
]
