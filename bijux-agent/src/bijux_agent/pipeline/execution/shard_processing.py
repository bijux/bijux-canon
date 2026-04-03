"""Helper functions handling shard creation and processing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias, cast

from bijux_agent.pipeline.termination import ExecutionTerminationReason

FinalStatus: TypeAlias = dict[str, Any]
IterationResult: TypeAlias = dict[str, Any]
ShardResult: TypeAlias = dict[str, Any]


async def shard_input(pipeline: Any, context: dict[str, Any]) -> list[dict[str, Any]]:
    text = context.get("text", "")
    if "file_path" in context and not text:
        file_result = await pipeline.file_reader.run(context)
        if "error" in file_result:
            pipeline.logger.error(
                "Failed to read file for sharding",
                extra={
                    "context": {
                        "error": file_result["error"],
                        "stage": "sharding",
                    }
                },
            )
            return [context]
        text = file_result.get("text", "")

    if not text or len(text) <= pipeline.shard_threshold:
        return [context]

    paragraphs = text.split("\n\n")
    shards: list[str] = []
    current_shard: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        if (
            current_length + paragraph_length > pipeline.shard_threshold
            and current_shard
        ):
            shards.append("\n\n".join(current_shard))
            current_shard = []
            current_length = 0
        current_shard.append(paragraph)
        current_length += paragraph_length

    if current_shard:
        shards.append("\n\n".join(current_shard))

    pipeline.logger.info(
        "Sharded input",
        extra={
            "context": {
                "shard_count": len(shards),
                "shard_threshold": pipeline.shard_threshold,
                "stage": "sharding",
            }
        },
    )
    pipeline.logger_manager.log_metric(
        "shards_created",
        len(shards),
        pipeline._metric_type.GAUGE,
        tags={"stage": "sharding"},
    )

    shard_contexts: list[dict[str, Any]] = []
    for i, shard in enumerate(shards):
        shard_context = context.copy()
        shard_context["text"] = shard
        shard_context["context_id"] = (
            f"{context.get('context_id', 'unknown')}_shard_{i}"
        )
        shard_contexts.append(shard_context)

    return shard_contexts


def _update_context(
    context: dict[str, Any], stage_result: dict[str, Any]
) -> dict[str, Any]:
    updated = context.copy()
    if "error" not in stage_result:
        if "text" in stage_result:
            updated["text"] = stage_result["text"]
        if "summary" in stage_result:
            updated["summary"] = stage_result["summary"]
        updated.update(
            {
                "summary_result": (
                    stage_result
                    if "summary" in stage_result
                    else updated.get("summary_result", {})
                ),
                "validation_result": (
                    stage_result
                    if "valid" in stage_result
                    else updated.get("validation_result", {})
                ),
                "critique_result": (
                    stage_result
                    if "critique_status" in stage_result
                    else updated.get("critique_result", {})
                ),
            }
        )
    return updated


async def process_shard(
    pipeline: Any,
    context: dict[str, Any],
    shard_idx: int,
    total_shards: int,
    required_stages: Sequence[Mapping[str, Any]],
) -> ShardResult:
    final_status: FinalStatus = {
        "success": False,
        "stages_processed": [],
        "iterations": 0,
        "termination_reason": ExecutionTerminationReason.COMPLETED,
        "converged": False,
        "convergence_reason": None,
        "convergence_iterations": 0,
    }
    shard_result: ShardResult = {
        "stages": {},
        "audit_trail": [],
        "revision_history": [],
        "execution_path": [],
        "warnings": [],
        "final_status": final_status,
    }
    current_context = context.copy()

    for iteration in range(1, pipeline.max_iterations + 1):
        pipeline.logger.info(
            "Shard iteration started",
            extra={
                "context": {
                    "shard_idx": shard_idx + 1,
                    "total_shards": total_shards,
                    "iteration": iteration,
                    "max_iterations": pipeline.max_iterations,
                    "stage": "shard_iteration",
                }
            },
        )
        iteration_result: IterationResult = {"iteration": iteration, "stages": {}}
        iteration_context = current_context.copy()

        pipeline.task_handler.set_stages(required_stages)
        task_result = await pipeline.task_handler.run(iteration_context)
        iteration_result["stages"] = task_result.get("stages", {})
        audit_entries = task_result.get("audit_trail", [])
        shard_result["audit_trail"].extend(
            cast(list[dict[str, Any]], audit_entries or [])
        )
        shard_result["warnings"].extend(task_result.get("warnings", []))

        shard_result["execution_path"].append(
            {
                "iteration": iteration,
                "stages": list(iteration_result["stages"].keys()),
            }
        )

        if "error" in task_result:
            pipeline.logger.error(
                "Shard iteration failed",
                extra={
                    "context": {
                        "shard_idx": shard_idx + 1,
                        "iteration": iteration,
                        "error": task_result["error"],
                        "stage": "shard_iteration",
                    }
                },
            )
            shard_result["final_status"] = {
                "success": False,
                "error": task_result["error"],
                "stages_processed": task_result.get("final_status", {}).get(
                    "stages_processed",
                    [],
                ),
                "iterations": task_result.get("final_status", {}).get(
                    "iterations",
                    0,
                ),
                "termination_reason": task_result.get("final_status", {}).get(
                    "termination_reason", ExecutionTerminationReason.FAILURE
                ),
                "converged": task_result.get("final_status", {}).get(
                    "converged", False
                ),
                "convergence_reason": task_result.get("final_status", {}).get(
                    "convergence_reason"
                ),
                "convergence_iterations": task_result.get("final_status", {}).get(
                    "convergence_iterations", 0
                ),
            }
            return shard_result

        iteration_context = _update_context(
            iteration_context, cast(dict[str, Any], task_result)
        )
        task_status = task_result.get("final_status", {})
        final_status["stages_processed"] = task_status.get("stages_processed", [])
        final_status["iterations"] = task_status.get("iterations", 0)
        final_status["termination_reason"] = task_status.get(
            "termination_reason", ExecutionTerminationReason.COMPLETED
        )
        final_status["converged"] = task_status.get("converged", False)
        final_status["convergence_reason"] = task_status.get("convergence_reason")
        final_status["convergence_iterations"] = task_status.get(
            "convergence_iterations", 0
        )

        critique_result = iteration_result["stages"].get("critique", {})
        feedback = await pipeline._apply_feedback_rules(
            "critique",
            critique_result,
            iteration_context,
        )
        going_for_retry = feedback.get("retry", False)
        if iteration == pipeline.max_iterations and going_for_retry:
            final_status["termination_reason"] = (
                ExecutionTerminationReason.RESOURCE_EXHAUSTION
            )
        if not going_for_retry or iteration == pipeline.max_iterations:
            shard_result["stages"] = iteration_result["stages"]
            break

        pipeline.logger.info(
            "Applying feedback for shard iteration",
            extra={
                "context": {
                    "shard_idx": shard_idx + 1,
                    "total_shards": total_shards,
                    "iteration": iteration,
                    "reason": feedback["reason"],
                    "stage": "feedback_loop",
                }
            },
        )
        current_context = feedback.get("updated_context", iteration_context)
        shard_result["revision_history"].append(
            {
                "iteration": iteration,
                "feedback": feedback,
                "context": current_context,
            }
        )
        pipeline.logger_manager.log_metric(
            "shard_iterations",
            1,
            pipeline._metric_type.COUNTER,
            tags={
                "shard_idx": str(shard_idx),
                "iteration": str(iteration),
                "stage": "shard_iteration",
            },
        )

    pipeline._notify_progress(
        f"Completed shard {shard_idx + 1}/{total_shards}",
        shard_idx + 1,
        total_shards,
    )

    return shard_result
