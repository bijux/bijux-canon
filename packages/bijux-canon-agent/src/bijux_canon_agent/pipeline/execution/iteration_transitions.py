"""State transition helpers for pipeline iteration execution."""

from __future__ import annotations

from typing import Any, cast

from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason

PipelineExecutionResult = dict[str, Any]
ShardResult = dict[str, Any]
ValidationResult = dict[str, Any]


def append_shard_result(
    pipeline_result: PipelineExecutionResult,
    shard_result: ShardResult,
) -> None:
    """Fold shard output into the mutable pipeline result."""
    audit_trail = cast(list[dict[str, Any]], pipeline_result["audit_trail"])
    revision_history = cast(list[dict[str, Any]], pipeline_result["revision_history"])
    execution_path = cast(list[dict[str, Any]], pipeline_result["execution_path"])
    warnings = cast(list[str], pipeline_result["warnings"])
    audit_trail.extend(shard_result.get("audit_trail", []))
    revision_history.extend(shard_result.get("revision_history", []))
    execution_path.extend(shard_result.get("execution_path", []))
    warnings.extend(shard_result.get("warnings", []))


def apply_shard_failure(
    pipeline_result: PipelineExecutionResult,
    shard_result: ShardResult,
) -> PipelineExecutionResult:
    """Record the terminal state for a shard-processing failure."""
    pipeline_result["final_status"] = {
        "success": False,
        "error": shard_result["error"],
        "stages_processed": shard_result.get("final_status", {}).get(
            "stages_processed",
            [],
        ),
        "iterations": shard_result.get("final_status", {}).get("iterations", 0),
        "termination_reason": ExecutionTerminationReason.FAILURE,
        "converged": False,
        "convergence_reason": None,
        "convergence_iterations": 0,
    }
    return pipeline_result


def apply_validation_failure(
    pipeline_result: PipelineExecutionResult,
    validation_result: ValidationResult,
) -> PipelineExecutionResult:
    """Record the terminal state for a final-result validation failure."""
    final_status = pipeline_result["final_status"]
    final_status["success"] = False
    issues = validation_result["issues"]
    if final_status.get("termination_reason") == ExecutionTerminationReason.COMPLETED:
        final_status["error"] = f"Final result does not meet task goal: {issues}"
        final_status["termination_reason"] = ExecutionTerminationReason.FAILURE
    else:
        final_status.setdefault("error", f"Validation issues: {issues}")
    pipeline_result["final_status"] = final_status
    return pipeline_result
