# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services consumed by the reason command transport."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_reason.application.run_artifacts import RunBuilder, RunInputs
from bijux_canon_reason.core.types import Plan, ProblemSpec
from bijux_canon_reason.evaluation.suite_workflow import run_eval_suite
from bijux_canon_reason.interfaces.serialization.json_file import (
    read_json_file,
    write_json_file,
)
from bijux_canon_reason.interfaces.serialization.trace_jsonl import read_trace_jsonl
from bijux_canon_reason.traces.replay import replay_from_artifacts
from bijux_canon_reason.verification.verifier import verify_trace


@dataclass(frozen=True)
class RunCommandResult:
    payload: dict[str, object]
    run_dir: Path
    verify_path: Path
    failure_count: int


@dataclass(frozen=True)
class VerifyCommandResult:
    payload: dict[str, object]
    output_path: Path
    failure_count: int


@dataclass(frozen=True)
class ReplayCommandResult:
    payload: dict[str, object]
    mismatch: bool


@dataclass(frozen=True)
class EvalCommandResult:
    payload: dict[str, object]
    summary_path: Path
    failed: int
    total: int


def execute_run_command(
    *, spec_path: Path, preset: str, seed: int, artifacts_dir: Path
) -> RunCommandResult:
    """Build, persist, and summarize one reasoning run."""
    spec = ProblemSpec.model_validate(read_json_file(spec_path))
    artifacts = RunBuilder().build(
        inputs=RunInputs(spec=spec, preset=preset, seed=seed),
        artifacts_root=artifacts_dir,
    )
    if artifacts.trace.id is None:
        raise RuntimeError("trace id missing (invariant violation)")
    report = artifacts.verify_report
    return RunCommandResult(
        payload={
            "run_dir": str(artifacts.run_dir),
            "verify_failures": len(report.failures),
            "summary": report.summary_metrics,
        },
        run_dir=artifacts.run_dir,
        verify_path=artifacts.verify_path,
        failure_count=len(report.failures),
    )


def execute_verify_command(*, trace_path: Path, plan_path: Path) -> VerifyCommandResult:
    """Verify a persisted trace against its declared plan."""
    trace = read_trace_jsonl(trace_path)
    if trace.id is None:
        raise RuntimeError("trace id missing (invariant violation)")
    plan = Plan.model_validate(read_json_file(plan_path))
    report = verify_trace(trace=trace, plan=plan, artifacts_dir=trace_path.parent)
    output_path = trace_path.parent / "verify.verify.json"
    write_json_file(output_path, report.model_dump(mode="json"))
    return VerifyCommandResult(
        payload={
            "status": "ok" if not report.failures else "failed",
            "failures": [failure.message for failure in report.failures],
            "checks": [check.model_dump(mode="json") for check in report.checks],
        },
        output_path=output_path,
        failure_count=len(report.failures),
    )


def execute_replay_command(trace_path: Path) -> ReplayCommandResult:
    """Replay a persisted trace and summarize exact fingerprint parity."""
    result, replay_trace = replay_from_artifacts(trace_path)
    payload: dict[str, object] = {
        "original_trace_fingerprint": result.original_trace_fingerprint,
        "replayed_trace_fingerprint": result.replayed_trace_fingerprint,
        "diff_summary": result.diff_summary,
        "replay_trace_path": str(replay_trace),
    }
    payload["original_fingerprint"] = payload["original_trace_fingerprint"]
    payload["replayed_fingerprint"] = payload["replayed_trace_fingerprint"]
    payload["diff"] = payload["diff_summary"]
    return ReplayCommandResult(
        payload=payload,
        mismatch=result.original_trace_fingerprint
        != result.replayed_trace_fingerprint,
    )


def execute_eval_command(
    *, suite: str, artifacts_dir: Path, preset: str, seed: int
) -> EvalCommandResult:
    """Run an admitted evaluation suite and summarize its persisted result."""
    result, summary_path = run_eval_suite(
        suite=suite,
        artifacts_dir=artifacts_dir,
        preset=preset,
        seed=seed,
    )
    return EvalCommandResult(
        payload={"summary": str(summary_path), **result.to_json()},
        summary_path=summary_path,
        failed=result.failed,
        total=result.total,
    )


__all__ = [
    "EvalCommandResult",
    "ReplayCommandResult",
    "RunCommandResult",
    "VerifyCommandResult",
    "execute_eval_command",
    "execute_replay_command",
    "execute_run_command",
    "execute_verify_command",
]
