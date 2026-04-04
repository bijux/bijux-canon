"""Execution flow contracts and helpers for stage running."""

from __future__ import annotations

from collections.abc import Sequence
import time
from typing import Any, NotRequired, TypedDict


class StageRunnerAuditEntry(TypedDict, total=False):
    """Audit trail entry for stage execution."""

    stage_name: str
    timestamp: str
    duration_sec: float
    error: str
    stages_processed: list[str]


class StageRunnerFinalStatus(TypedDict):
    """Final status block for stage execution."""

    stages_processed: list[str]
    iterations: int


class StageRunnerResult(TypedDict):
    """Typed output for StageRunnerAgent runs."""

    stages: dict[str, dict[str, Any]]
    final_status: StageRunnerFinalStatus
    audit_trail: list[StageRunnerAuditEntry]
    warnings: list[str]
    error: NotRequired[str]
    action_plan: NotRequired[list[str]]


def initialize_stage_runner_result() -> StageRunnerResult:
    """Create the initial result envelope for stage execution."""
    return {
        "stages": {},
        "final_status": {"stages_processed": [], "iterations": 0},
        "audit_trail": [],
        "warnings": [],
    }


def build_stage_inputs(
    current_context: dict[str, Any],
    result: StageRunnerResult,
    dependencies: Sequence[str],
) -> dict[str, Any]:
    """Build the stage input payload from current context and dependencies."""
    inputs: dict[str, Any] = {}
    for dependency in dependencies:
        if dependency in result["stages"]:
            inputs.update(result["stages"][dependency])
    inputs.update(current_context)
    return inputs


def add_stage_warning(result: StageRunnerResult, warning_msg: str) -> None:
    """Append a warning to the stage-runner result."""
    result["warnings"].append(warning_msg)


def record_stage_success(
    result: StageRunnerResult,
    *,
    stage_name: str,
    stage_output: dict[str, Any],
    stage_duration: float,
) -> None:
    """Record a successful stage execution."""
    result["stages"][stage_name] = stage_output
    result["final_status"]["stages_processed"].append(stage_name)
    result["audit_trail"].append(
        {
            "stage_name": stage_name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": round(stage_duration, 2),
        }
    )


def record_completion(result: StageRunnerResult, duration: float) -> None:
    """Append the final execution audit entry."""
    result["audit_trail"].append(
        {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": round(duration, 2),
            "stages_processed": result["final_status"]["stages_processed"],
        }
    )
