"""Iteration and completion helpers for pipeline execution."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from bijux_canon_agent.pipeline.execution.shard_processing import process_shard
from bijux_canon_agent.pipeline.execution.telemetry import PipelineExecutionContext
from bijux_canon_agent.pipeline.execution.iteration_transitions import (
    append_shard_result,
    apply_shard_failure,
    apply_validation_failure,
)

PipelineExecutionResult = dict[str, Any]
ShardResult = dict[str, Any]
MergedShardResult = dict[str, Any]

PreparationT = TypeVar("PreparationT", bound="_PreparedExecutionState")
IterationT = TypeVar("IterationT", covariant=True)
ConvergenceT = TypeVar("ConvergenceT", covariant=True)
FailedT = TypeVar("FailedT", covariant=True)


class _ExecutionHooks(Protocol):
    async def _merge_shard_results(
        self,
        shard_results: list[ShardResult],
        required_stages: list[dict[str, Any]],
    ) -> MergedShardResult: ...

    async def _extract_final_result(
        self, stages: dict[str, dict[str, Any]], task_goal: str
    ) -> Any: ...

    async def _validate_final_result(
        self, result: Any, task_goal: str, context_id: str | None = None
    ) -> dict[str, Any]: ...


class _PreparedExecutionState(Protocol):
    @property
    def context_id(self) -> str: ...

    @property
    def cache_key(self) -> str: ...

    @property
    def task_goal(self) -> str: ...

    @property
    def shards(self) -> list[dict[str, Any]]: ...

    @property
    def required_stages(self) -> list[dict[str, Any]]: ...

    @property
    def pipeline_result(self) -> PipelineExecutionResult: ...

    @property
    def execution_context(self) -> PipelineExecutionContext: ...


class _IterationState(Protocol):
    @property
    def context_id(self) -> str: ...

    @property
    def cache_key(self) -> str: ...

    @property
    def task_goal(self) -> str: ...

    @property
    def shards(self) -> list[dict[str, Any]]: ...

    @property
    def final_result(self) -> Any: ...

    @property
    def pipeline_result(self) -> PipelineExecutionResult: ...

    @property
    def execution_context(self) -> PipelineExecutionContext: ...


class _ConvergenceState(Protocol):
    @property
    def context_id(self) -> str: ...

    @property
    def cache_key(self) -> str: ...

    @property
    def shards(self) -> list[dict[str, Any]]: ...

    @property
    def pipeline_result(self) -> PipelineExecutionResult: ...

    @property
    def execution_context(self) -> PipelineExecutionContext: ...


class _IterationCtor(Protocol[IterationT]):
    def __call__(
        self,
        *,
        context_id: str,
        cache_key: str,
        task_goal: str,
        shards: list[dict[str, Any]],
        required_stages: list[dict[str, Any]],
        shard_results: list[ShardResult],
        final_result: Any,
        pipeline_result: PipelineExecutionResult,
        execution_context: PipelineExecutionContext,
    ) -> IterationT: ...


class _ConvergenceCtor(Protocol[ConvergenceT]):
    def __call__(
        self,
        *,
        context_id: str,
        cache_key: str,
        task_goal: str,
        shards: list[dict[str, Any]],
        pipeline_result: PipelineExecutionResult,
        execution_context: PipelineExecutionContext,
    ) -> ConvergenceT: ...


class _FailedCtor(Protocol[FailedT]):
    def __call__(self, result: PipelineExecutionResult) -> FailedT: ...


class _ExecutionOwner(_ExecutionHooks, Protocol):
    logger: Any
    logger_manager: Any
    _metric_type: Any
    _cache: dict[str, PipelineExecutionResult] | None

    def _persist_pipeline_result(
        self, result: PipelineExecutionResult, context_id: str
    ) -> None: ...


async def execute_iteration_state(
    owner: _ExecutionOwner,
    preparation: PreparationT,
    *,
    iteration_cls: _IterationCtor[IterationT],
    failed_cls: _FailedCtor[FailedT],
) -> IterationT | FailedT:
    """Execute all prepared shards and produce the merged iteration result."""
    shard_results: list[ShardResult] = []
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
        append_shard_result(preparation.pipeline_result, shard_result)

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
            return failed_cls(
                apply_shard_failure(preparation.pipeline_result, shard_result)
            )

    merged_result = await owner._merge_shard_results(
        shard_results, preparation.required_stages
    )
    preparation.pipeline_result["stages"] = merged_result["stages"]
    preparation.pipeline_result["final_status"] = merged_result["final_status"]

    final_result = await owner._extract_final_result(
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


async def apply_convergence_result(
    owner: _ExecutionOwner,
    iteration: _IterationState,
    *,
    convergence_cls: _ConvergenceCtor[ConvergenceT],
    failed_cls: _FailedCtor[FailedT],
) -> ConvergenceT | FailedT:
    """Validate final results and convert them to convergence state."""
    validation_result = await owner._validate_final_result(
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
        return failed_cls(
            apply_validation_failure(iteration.pipeline_result, validation_result)
        )

    return convergence_cls(
        context_id=iteration.context_id,
        cache_key=iteration.cache_key,
        task_goal=iteration.task_goal,
        shards=iteration.shards,
        pipeline_result=iteration.pipeline_result,
        execution_context=iteration.execution_context,
    )


async def finalize_execution_result(
    owner: _ExecutionOwner,
    convergence: _ConvergenceState,
) -> PipelineExecutionResult:
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

    owner._persist_pipeline_result(convergence.pipeline_result, convergence.context_id)
    return convergence.pipeline_result


__all__ = [
    "apply_convergence_result",
    "execute_iteration_state",
    "finalize_execution_result",
]
