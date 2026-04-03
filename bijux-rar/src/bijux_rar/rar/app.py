# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bijux_rar.core.rar_types import (
    Plan,
    ProblemSpec,
    RuntimeDescriptor,
    Trace,
    VerificationReport,
)
from bijux_rar.rar.execution.executor import ExecutionPolicy, execute_plan
from bijux_rar.rar.execution.runtime import Runtime
from bijux_rar.rar.planning.planner import plan_problem
from bijux_rar.rar.verification.verifier import verify_trace
from bijux_rar.system_contract import assert_system_contract


@dataclass(frozen=True)
class AppResult:
    spec: ProblemSpec
    plan: Plan
    trace: Trace
    verify_report: VerificationReport
    runtime_descriptor: RuntimeDescriptor


def run_app(
    *,
    spec: ProblemSpec,
    preset: str,
    seed: int,
    artifacts_dir: Path | None = None,
    runtime: Any | None = None,
) -> AppResult:
    assert_system_contract()
    spec_with_id = spec if spec.id else spec.with_content_id()
    plan = plan_problem(spec=spec_with_id, preset=preset)
    rt: Any = (
        runtime
        if runtime is not None
        else Runtime.fake(seed=seed, artifacts_dir=artifacts_dir)
    )
    execution = execute_plan(
        spec=spec_with_id, plan=plan, runtime=rt, policy=ExecutionPolicy(fail_fast=True)
    )
    trace = execution.trace
    verify_report = verify_trace(trace=trace, plan=plan, artifacts_dir=artifacts_dir)
    return AppResult(
        spec=spec_with_id,
        plan=plan,
        trace=trace,
        verify_report=verify_report,
        runtime_descriptor=rt.descriptor,
    )
