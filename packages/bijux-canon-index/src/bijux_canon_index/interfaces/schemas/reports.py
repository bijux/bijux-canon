# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Reports schemas for interface payloads."""

from __future__ import annotations

from bijux_canon_index.interfaces.schemas.base import StrictModel


class StorageBackendDescriptor(StrictModel):
    """Represents storage backend descriptor."""
    name: str
    status: str
    persistence: str | None = None
    notes: str | None = None


class VectorStoreDescriptor(StrictModel):
    """Represents vector store descriptor."""
    name: str
    available: bool
    supports_exact: bool
    supports_ann: bool
    delete_supported: bool
    filtering_supported: bool
    deterministic_exact: bool
    experimental: bool
    consistency: str | None = None
    version: str | None = None
    notes: str | None = None


class BackendCapabilitiesReport(StrictModel):
    """Represents backend capabilities report."""
    backend: str
    contracts: list[str]
    deterministic_query: bool | None
    supports_ann: bool
    replayable: bool | None
    metrics: list[str]
    max_vector_size: int | None
    isolation_level: str | None
    execution_modes: list[str]
    ann_status: str
    storage_backends: list[StorageBackendDescriptor]
    vector_stores: list[VectorStoreDescriptor]
    plugins: dict[str, list[dict[str, object]]]
    nd: dict[str, object] | None = None


__all__ = [
    "BackendCapabilitiesReport",
    "StorageBackendDescriptor",
    "VectorStoreDescriptor",
]
