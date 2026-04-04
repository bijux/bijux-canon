# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_reason.core.types import (
    Plan,
    ProblemSpec,
    RuntimeDescriptor,
    Trace,
    VerificationReport,
)
from bijux_canon_reason.execution.executor import ExecutionPolicy, execute_plan
from bijux_canon_reason.execution.runtime import ExecutionRuntime, Runtime
from bijux_canon_reason.planning.planner import plan_problem
from bijux_canon_reason.verification.verifier import verify_trace
from bijux_canon_reason.core.system_contract import assert_system_contract


@dataclass(frozen=True)
class RunWorkflowResult:
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
    runtime: ExecutionRuntime | None = None,
) -> RunWorkflowResult:
    assert_system_contract()
    spec_with_id = spec if spec.id else spec.with_content_id()
    plan = plan_problem(spec=spec_with_id, preset=preset)
    rt = _resolve_runtime(seed=seed, artifacts_dir=artifacts_dir, runtime=runtime)
    execution = execute_plan(
        spec=spec_with_id, plan=plan, runtime=rt, policy=ExecutionPolicy(fail_fast=True)
    )
    trace = execution.trace
    verify_report = verify_trace(trace=trace, plan=plan, artifacts_dir=artifacts_dir)
    return RunWorkflowResult(
        spec=spec_with_id,
        plan=plan,
        trace=trace,
        verify_report=verify_report,
        runtime_descriptor=rt.descriptor,
    )


def _resolve_runtime(
    *,
    seed: int,
    artifacts_dir: Path | None,
    runtime: ExecutionRuntime | None,
) -> ExecutionRuntime:
    if runtime is not None:
        return runtime
    return Runtime.fake(seed=seed, artifacts_dir=artifacts_dir)
