# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_reason.core.types import JsonValue, Plan, ProblemSpec, TraceEventKind
from bijux_canon_reason.execution.executor import ExecutionPolicy, execute_plan
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.execution.tool_runtime import FakeTool, ToolRegistry
from bijux_canon_reason.planning.planner import plan_problem
import pytest


class ExplodingTool:
    version = "1.0.0"
    config_fingerprint = "failing-tool"

    def invoke(self, *, arguments: dict[str, JsonValue], seed: int) -> JsonValue:
        raise RuntimeError("retrieval backend unavailable")


def _build_runtime(tmp_path: Path) -> Runtime:
    return Runtime(
        seed=0,
        tools=ToolRegistry(
            tools={
                "retrieve": ExplodingTool(),
                "compute": FakeTool(name="compute"),
            }
        ),
        runtime_kind="ExplodingRuntime",
        mode="live",
        artifacts_dir=tmp_path,
    )


def _build_plan() -> tuple[ProblemSpec, Plan]:
    spec = ProblemSpec(
        description="What is Rust?",
        constraints={"needs_retrieval": True, "min_supports_per_claim": 1},
    )
    return spec, plan_problem(spec=spec, preset="rar")


def test_executor_fail_fast_raises_on_tool_failure(tmp_path: Path) -> None:
    spec, plan = _build_plan()

    with pytest.raises(RuntimeError, match="tool failure"):
        execute_plan(
            spec=spec,
            plan=plan,
            runtime=_build_runtime(tmp_path),
            policy=ExecutionPolicy(fail_fast=True),
        )


def test_executor_can_continue_after_tool_failure(tmp_path: Path) -> None:
    spec, plan = _build_plan()

    result = execute_plan(
        spec=spec,
        plan=plan,
        runtime=_build_runtime(tmp_path),
        policy=ExecutionPolicy(fail_fast=False),
    )

    tool_returns = [
        event
        for event in result.trace.events
        if event.kind == TraceEventKind.tool_returned
    ]
    assert tool_returns
    assert tool_returns[0].result.success is False

    finished_outputs = [
        event.output.type
        for event in result.trace.events
        if event.kind == TraceEventKind.step_finished
    ]
    assert "insufficient_evidence" in finished_outputs
