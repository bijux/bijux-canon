# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import multiprocessing
import os
import signal
from pathlib import Path

import bijux_rar
import duckdb
import pytest

from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.runtime.orchestration.planner import ExecutionPlanner
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.ontology.ids import AgentID, BundleID, RunID, TenantID

pytestmark = pytest.mark.regression


def _run_with_crash(db_path: str, resolved_flow, verification_policy) -> None:
    os.environ["AF_CRASH_AT_STEP"] = "0"
    resolved_flow = ExecutionPlanner().resolve(resolved_flow.manifest)
    bijux_rar.reason = lambda **_kwargs: ReasoningBundle(
        spec_version="v1",
        bundle_id=BundleID("bundle-crash"),
        claims=(),
        steps=(),
        evidence_ids=(),
        producer_agent_id=AgentID("agent-a"),
    )
    execution_store = DuckDBExecutionWriteStore(Path(db_path))
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
            verification_policy=verification_policy,
        ),
    )
    if result.run_id is not None and result.trace is not None:
        last_step = max(event.step_index for event in result.trace.events)
        execution_store.save_checkpoint(
            run_id=result.run_id,
            tenant_id=result.trace.tenant_id,
            step_index=last_step,
            event_index=result.trace.events[-1].event_index,
        )
    os.kill(os.getpid(), signal.SIGKILL)


def test_crash_recovery_resume(
    tmp_path: Path,
    resolved_flow,
    baseline_policy,
) -> None:
    db_path = tmp_path / "crash.duckdb"
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_run_with_crash,
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
