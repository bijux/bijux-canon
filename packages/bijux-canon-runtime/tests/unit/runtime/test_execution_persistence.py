# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_runtime.application.execution_persistence import persist_run
from bijux_canon_runtime.application.execution_persistence import resolve_read_store
from bijux_canon_runtime.application.flow_execution_models import ExecutionConfig
from bijux_canon_runtime.application.flow_execution_models import FlowRunResult
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)


def test_resolve_read_store_uses_duckdb_write_store_path(tmp_path: Path) -> None:
    write_store = DuckDBExecutionWriteStore(tmp_path / "runtime.duckdb")
    read_store = resolve_read_store(
        ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=None,
            execution_store=write_store,
        )
    )

    assert isinstance(read_store, DuckDBExecutionReadStore)


def test_persist_run_assigns_run_id_when_registering_new_run(
    execution_store,
    resolved_flow,
) -> None:
    result = persist_run(
        FlowRunResult(
            resolved_flow=resolved_flow,
            trace=None,
            artifacts=[],
            evidence=[],
            reasoning_bundles=[],
            verification_results=[],
            verification_arbitrations=[],
            run_id=None,
        ),
        ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=resolved_flow.plan.determinism_level,
            execution_store=execution_store,
        ),
    )

    assert result.run_id is not None
