# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Crash-recovery worker helpers for multiprocessing regression tests."""

from __future__ import annotations

import os
from pathlib import Path
import signal
from typing import Any

import bijux_canon_index
import bijux_canon_reason

from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import AgentID, BundleID


def run_with_crash(
    db_path: str,
    resolved_flow: Any,
    verification_policy: Any,
) -> None:
    """Execute a live run, persist a checkpoint, and terminate abruptly."""
    os.environ["AF_CRASH_AT_STEP"] = "0"
    planned_flow = ExecutionPlanner().resolve(resolved_flow.manifest)
    bijux_canon_index.enforce_contract = lambda *_args, **_kwargs: True
    bijux_canon_reason.reason = lambda **_kwargs: ReasoningBundle(
        spec_version="v1",
        bundle_id=BundleID("bundle-crash"),
        claims=(),
        steps=(),
        evidence_ids=(),
        producer_agent_id=AgentID("agent-a"),
    )
    execution_store = DuckDBExecutionWriteStore(Path(db_path))
    result = execute_flow(
        resolved_flow=planned_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=planned_flow.manifest.determinism_level,
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
