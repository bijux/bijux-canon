"""Preparation and failure helpers for pipeline execution."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from bijux_canon_agent.pipeline.agent_registry import determine_execution_plan
from bijux_canon_agent.pipeline.execution.shard_processing import shard_input
from bijux_canon_agent.pipeline.execution.telemetry import PipelineExecutionContext
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


async def prepare_execution_state(
    owner,
    context: dict[str, Any],
    *,
    prepared_cls,
    cached_cls,
    failed_cls,
):
    """Prepare a pipeline execution request for iteration."""
    context_id = context.get(
        "context_id",
        hashlib.sha256(str(sorted(context.items())).encode()).hexdigest(),
    )
    owner.reset_telemetry()
    with owner.logger.context(agent="Pipeline", context_id=context_id):
        owner.logger.info(
            "Pipeline execution started",
            extra={
                "context": {
                    "context_id": context_id,
                    "input_keys": list(context.keys()),
                    "task_goal": context.get("task_goal", "undefined"),
                }
            },
        )

    pipeline_result: dict[str, Any] = {
        "result": None,
        "stages": {},
        "audit_trail": [],
        "final_status": {
            "success": False,
            "stages_processed": [],
            "iterations": 0,
            "termination_reason": ExecutionTerminationReason.COMPLETED,
            "converged": False,
            "convergence_reason": None,
            "convergence_iterations": 0,
        },
        "cache_hit": False,
        "revision_history": [],
        "telemetry": {},
        "execution_path": [],
        "warnings": [],
    }
    execution_context = PipelineExecutionContext(
        audit_trail=pipeline_result["audit_trail"],
        revision_history=pipeline_result["revision_history"],
    )
    pipeline_result["telemetry"] = execution_context.baseline()
    owner.audit_trail = []
    owner.revision_history = []

    cache_key = owner._generate_cache_key(context)
    if owner._cache is not None and cache_key in owner._cache:
        owner.logger.debug(
            "Returning cached pipeline result",
            extra={"context": {"cache_key": cache_key}},
        )
        cached_result = dict(owner._cache[cache_key])
        cached_result["cache_hit"] = True
        owner.logger_manager.log_metric(
            "pipeline_cache_hits",
            1,
            owner._metric_type.COUNTER,
            tags={"stage": "cache_check"},
        )
        return cached_cls(cached_result)

    if not context or "task_goal" not in context:
        error_msg = "Input context must provide 'task_goal' to define the task objective"
        owner.logger.error(
            error_msg,
            extra={"context": {"stage": "input_validation"}},
        )
        owner.logger_manager.log_metric(
            "input_validation_errors",
            1,
            owner._metric_type.COUNTER,
            tags={"stage": "input_validation"},
        )
        error_result = await build_error_result(
            owner,
            error_msg,
            context,
            stage="input_validation",
        )
        return failed_cls(error_result)

    current_context = context.copy()
    task_goal = context["task_goal"].lower()

    required_stages = (
        owner._stages
        if owner._stages
        else determine_execution_plan(owner, task_goal)
    )
    owner.logger.info(
        "Determined required stages for task",
        extra={
            "context": {
                "task_goal": task_goal,
                "required_stages": [stage["name"] for stage in required_stages],
                "stage": "stage_configuration",
            }
        },
    )

    shards = await shard_input(owner, current_context)
    return prepared_cls(
        context_id=context_id,
        cache_key=cache_key,
        context=current_context,
        task_goal=task_goal,
        required_stages=required_stages,
        shards=shards,
        pipeline_result=pipeline_result,
        execution_context=execution_context,
    )


async def build_error_result(
    owner,
    msg: str,
    context: dict[str, Any] | None = None,
    *,
    stage: str = "pipeline",
) -> dict[str, Any]:
    """Build the standardized pipeline execution error result."""
    result: dict[str, Any] = {
        "result": None,
        "stages": {},
        "audit_trail": [
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "duration_sec": 0.0,
                "error": msg,
            }
        ],
        "final_status": {
            "success": False,
            "error": msg,
            "stages_processed": [],
            "iterations": 0,
            "termination_reason": ExecutionTerminationReason.FAILURE,
            "converged": False,
            "convergence_reason": None,
            "convergence_iterations": 0,
        },
        "cache_hit": False,
        "revision_history": [],
        "execution_path": [],
        "warnings": [msg],
        "telemetry": {"iterations": 0, "stages_executed": 0},
        "error": msg,
        "action_plan": [f"Resolve error: {msg}"],
    }
    await owner.logger.async_log(
        "ERROR",
        msg,
        {
            "stage": stage,
            "context_id": context.get("context_id", "unknown") if context else "error",
        },
    )
    owner.logger_manager.log_metric(
        "pipeline_errors",
        1,
        owner._metric_type.COUNTER,
        tags={"stage": stage},
    )
    return result


__all__ = ["build_error_result", "prepare_execution_state"]
