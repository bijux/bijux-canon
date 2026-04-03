"""Iteration and completion helpers for pipeline execution."""

from __future__ import annotations

from typing import Any, cast

from bijux_canon_agent.pipeline.execution.shard_processing import process_shard
from bijux_canon_agent.pipeline.termination import ExecutionTerminationReason


async def execute_iteration_state(
    owner,
    preparation,
    *,
    iteration_cls,
    failed_cls,
):
    """Execute all prepared shards and produce the merged iteration result."""
    shard_results: list[dict[str, Any]] = []
    for shard_idx, shard_context in enumerate(preparation.shards):
        owner.logger.info(
            "Processing shard",
            extra={
                "context": {
                    "shard_idx": shard_idx + 1,
                    "total_shards": len(preparation.shards),
                    "stage": "sharding",
                }
            },
        )
        shard_result = await process_shard(
            owner,
            shard_context,
            shard_idx,
            len(preparation.shards),
            preparation.required_stages,
        )
        shard_results.append(shard_result)

        audit_trail = cast(list[dict[str, Any]], preparation.pipeline_result["audit_trail"])
        revision_history = cast(
            list[dict[str, Any]], preparation.pipeline_result["revision_history"]
        )
        execution_path = cast(
            list[dict[str, Any]], preparation.pipeline_result["execution_path"]
        )
        warnings = cast(list[str], preparation.pipeline_result["warnings"])
        audit_trail.extend(shard_result.get("audit_trail", []))
        revision_history.extend(shard_result.get("revision_history", []))
        execution_path.extend(shard_result.get("execution_path", []))
        warnings.extend(shard_result.get("warnings", []))

        if "error" in shard_result:
            owner.logger.error(
                "Shard processing failed",
                extra={
                    "context": {
                        "shard_idx": shard_idx + 1,
                        "error": shard_result["error"],
                        "stage": "shard_processing",
                    }
                },
            )
            preparation.pipeline_result["final_status"] = {
                "success": False,
                "error": shard_result["error"],
                "stages_processed": shard_result.get("final_status", {}).get(
                    "stages_processed",
                    [],
                ),
                "iterations": shard_result.get("final_status", {}).get(
                    "iterations",
                    0,
                ),
                "termination_reason": ExecutionTerminationReason.FAILURE,
                "converged": False,
                "convergence_reason": None,
                "convergence_iterations": 0,
            }
            return failed_cls(preparation.pipeline_result)

    hooks = cast(object, owner)
    merged_result = await hooks._merge_shard_results(
        shard_results, preparation.required_stages
    )
    preparation.pipeline_result["stages"] = merged_result["stages"]
    preparation.pipeline_result["final_status"] = merged_result["final_status"]

    final_result = await hooks._extract_final_result(
        merged_result["stages"], preparation.task_goal
    )
    preparation.pipeline_result["result"] = final_result

    return iteration_cls(
        context_id=preparation.context_id,
        cache_key=preparation.cache_key,
        task_goal=preparation.task_goal,
        shards=preparation.shards,
        required_stages=preparation.required_stages,
        shard_results=shard_results,
        final_result=final_result,
        pipeline_result=preparation.pipeline_result,
        execution_context=preparation.execution_context,
    )


async def apply_convergence_result(owner, iteration, *, convergence_cls, failed_cls):
    """Validate final results and convert them to convergence state."""
    hooks = cast(object, owner)
    validation_result = await hooks._validate_final_result(
        iteration.final_result, iteration.task_goal, iteration.context_id
    )
    if not validation_result["is_valid"]:
        owner.logger.warning(
            "Final result does not meet task goal requirements",
            extra={
                "context": {
                    "task_goal": iteration.task_goal,
                    "validation_issues": validation_result["issues"],
                    "stage": "final_validation",
                }
            },
        )
        final_status = iteration.pipeline_result["final_status"]
        final_status["success"] = False
        if (
            final_status.get("termination_reason")
            == ExecutionTerminationReason.COMPLETED
        ):
            final_status["error"] = (
                f"Final result does not meet task goal: {validation_result['issues']}"
            )
            final_status["termination_reason"] = ExecutionTerminationReason.FAILURE
        else:
            final_status.setdefault(
                "error",
                f"Validation issues: {validation_result['issues']}",
            )
        iteration.pipeline_result["final_status"] = final_status
        return failed_cls(iteration.pipeline_result)

    return convergence_cls(
        context_id=iteration.context_id,
        cache_key=iteration.cache_key,
        task_goal=iteration.task_goal,
        shards=iteration.shards,
        pipeline_result=iteration.pipeline_result,
        execution_context=iteration.execution_context,
    )


async def finalize_execution_result(owner, convergence) -> dict[str, Any]:
    """Finalize telemetry, cache storage, and artifact persistence."""
    convergence.pipeline_result["telemetry"] = convergence.execution_context.finalize(
        len(convergence.shards)
    )
    duration = convergence.pipeline_result["telemetry"]["total_duration"]
    owner.logger.info(
        "Pipeline execution completed",
        extra={
            "context": {
                "total_duration": duration,
                "shards_processed": len(convergence.shards),
                "iterations": convergence.pipeline_result["telemetry"]["iterations"],
                "stages_executed": convergence.pipeline_result["telemetry"][
                    "stages_executed"
                ],
                "stage": "completion",
            }
        },
    )
    owner.logger_manager.log_metric(
        "pipeline_executions",
        1,
        owner._metric_type.COUNTER,
        tags={
            "status": (
                "success"
                if convergence.pipeline_result["final_status"]["success"]
                else "failed"
            ),
            "stage": "completion",
        },
    )

    cache = owner._cache
    if cache is not None:
        cache[convergence.cache_key] = convergence.pipeline_result
        owner._cache = cache
        owner.logger_manager.log_metric(
            "cache_stores",
            1,
            owner._metric_type.COUNTER,
            tags={"stage": "cache_store"},
        )

    owner._persist_pipeline_result(
        convergence.pipeline_result, convergence.context_id
    )
    return convergence.pipeline_result


__all__ = [
    "apply_convergence_result",
    "execute_iteration_state",
    "finalize_execution_result",
]
