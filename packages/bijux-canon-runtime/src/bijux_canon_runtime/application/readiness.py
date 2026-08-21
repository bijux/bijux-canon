# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Runtime readiness application service."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)


def runtime_store_is_ready(db_path: Path) -> bool:
    """Return whether the configured execution store can be opened and closed."""
    try:
        store = DuckDBExecutionStore(db_path)
        store.close()
    except Exception:
        return False
    return True


__all__ = ["runtime_store_is_ready"]
