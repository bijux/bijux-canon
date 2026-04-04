# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""
Minimal pgvector adapter that delegates to SQLite-backed resources.

This provides a reference external-backend surface without introducing network
dependencies; it exercises the same contracts under a distinct backend name.
"""

from __future__ import annotations

from bijux_canon_index.contracts.resources import (
    BackendCapabilities,
    ExecutionResources,
)
from bijux_canon_index.core.v1_exclusions import ensure_excluded
from bijux_canon_index.infra.adapters.sqlite.backend import (
    SQLiteFixture,
    sqlite_backend,
)
from bijux_canon_index.infra.runtime_paths import default_pgvector_state_path


def pgvector_backend(path: str | None = None) -> SQLiteFixture:
    """Return execution resources that mimic a pgvector backend."""
    ensure_excluded("pgvector_backend")
    base = sqlite_backend(path or str(default_pgvector_state_path()))
    caps = base.stores.capabilities
    capabilities = (
        BackendCapabilities(
            contracts=caps.contracts if caps else None,
            max_vector_size=caps.max_vector_size if caps else None,
            metrics=caps.metrics if caps else None,
            deterministic_query=caps.deterministic_query if caps else None,
            replayable=caps.replayable if caps else None,
            isolation_level=caps.isolation_level if caps else None,
            ann_support=True,
        )
        if caps
        else BackendCapabilities(contracts=None, ann_support=True)
    )
    stores = ExecutionResources(
        name="pgvector",
        vectors=base.stores.vectors,
        ledger=base.stores.ledger,
        capabilities=capabilities,
    )
    return SQLiteFixture(
        tx_factory=base.tx_factory,
        stores=stores,
        authz=base.authz,
        name="pgvector",
        ann=base.ann,
        diagnostics=base.diagnostics,
    )


__all__ = ["pgvector_backend"]
