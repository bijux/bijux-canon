# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import multiprocessing
from pathlib import Path

from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.testing.crash_recovery import run_with_crash
from bijux_canon_runtime.ontology.ids import RunID, TenantID
import duckdb
import pytest

pytestmark = pytest.mark.regression


def test_crash_recovery_resume(
    tmp_path: Path,
    resolved_flow,
    baseline_policy,
) -> None:
    db_path = tmp_path / "crash.duckdb"
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=run_with_crash,
        args=(str(db_path), resolved_flow, baseline_policy),
    )
    process.start()
    process.join()
    assert process.exitcode != 0

    connection = duckdb.connect(str(db_path))
    row = connection.execute(
        "SELECT run_id FROM runs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    run_id = RunID(row[0])

    execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=DuckDBExecutionWriteStore(db_path),
            verification_policy=baseline_policy,
            resume_run_id=run_id,
        ),
    )

    read_store = DuckDBExecutionReadStore(db_path)
    trace = read_store.load_trace(run_id, tenant_id=TenantID("tenant-a"))
    assert trace.finalized is True
    checkpoint = read_store.load_checkpoint(run_id, tenant_id=TenantID("tenant-a"))
    assert checkpoint is not None
    assert checkpoint[0] == 0
    assert all(
        earlier.event_index < later.event_index
        for earlier, later in zip(trace.events, trace.events[1:], strict=False)
    )
