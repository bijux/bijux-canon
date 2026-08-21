# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application service for persisted runtime inspection."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.observability.analysis.trace_diff import semantic_trace_diff
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
)
from bijux_canon_runtime.ontology.ids import RunID, TenantID


def load_run_trace(*, db_path: Path, run_id: str, tenant_id: str) -> ExecutionTrace:
    """Load one persisted trace through the runtime storage adapter."""
    store = DuckDBExecutionReadStore(db_path)
    return store.load_trace(RunID(run_id), tenant_id=TenantID(tenant_id))


def compare_run_traces(
    *, db_path: Path, run_a: str, run_b: str, tenant_id: str
) -> dict[str, object]:
    """Return the semantic difference between two persisted traces."""
    trace_a = load_run_trace(db_path=db_path, run_id=run_a, tenant_id=tenant_id)
    trace_b = load_run_trace(db_path=db_path, run_id=run_b, tenant_id=tenant_id)
    return semantic_trace_diff(
        trace_a,
        trace_b,
        acceptability=trace_a.replay_acceptability,
    )


def validate_execution_store(db_path: Path) -> None:
    """Open the runtime execution store and validate its schema."""
    DuckDBExecutionReadStore(db_path)


__all__ = ["compare_run_traces", "load_run_trace", "validate_execution_store"]
