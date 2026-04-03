"""Execution helpers for the pipeline orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from typing import Any, Protocol, TypeAlias, cast

from bijux_canon_agent.pipeline.execution.io import PipelineIOMixin
from bijux_canon_agent.pipeline.execution.iteration_support import (
    apply_convergence_result,
    execute_iteration_state,
    finalize_execution_result,
)
from bijux_canon_agent.pipeline.execution.preparation_support import (
    build_error_result,
    prepare_execution_state,
)
from bijux_canon_agent.pipeline.execution.telemetry import PipelineExecutionContext

PipelineExecutionResult: TypeAlias = dict[str, Any]
ShardResult: TypeAlias = dict[str, Any]
MergedShardResult: TypeAlias = dict[str, Any]


class _ResultsHooks(Protocol):
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


class PipelineExecutionMixin(PipelineIOMixin):
    """Mix-in encapsulating `run`/`revise` behavior."""

    logger: Any
    logger_manager: Any
    _metric_type: Any
    max_iterations: int
    shard_threshold: int
    stage_timeout: float
    policy: dict[str, Any]
    _cache: dict[str, PipelineExecutionResult] | None
    _stages: list[dict[str, Any]]
    results_dir: Path
    feedback_rules: dict[str, Any]
    progress_callback: Callable[[str, float, float], Any] | None
    _progress_tasks: list[asyncio.Task[Any]]
    audit_trail: list[dict[str, Any]]
    revision_history: list[dict[str, Any]]
    file_reader: Any
    summarizer: Any
    validator: Any
    critique: Any
    stage_runner: Any

    def reset_telemetry(self) -> None: ...

    @dataclass(frozen=True)
    class CachedExecution:
        result: PipelineExecutionResult

    @dataclass(frozen=True)
    class FailedExecution:
        result: PipelineExecutionResult

    @dataclass(frozen=True)
    class PreparedExecution:
        context_id: str
        cache_key: str
        context: dict[str, Any]
        task_goal: str
        required_stages: list[dict[str, Any]]
        shards: list[dict[str, Any]]
        pipeline_result: PipelineExecutionResult
        execution_context: PipelineExecutionContext

    @dataclass(frozen=True)
    class IterationResult:
        context_id: str
        cache_key: str
        task_goal: str
        shards: list[dict[str, Any]]
        required_stages: list[dict[str, Any]]
        shard_results: list[ShardResult]
        final_result: Any
        pipeline_result: PipelineExecutionResult
        execution_context: PipelineExecutionContext

    @dataclass(frozen=True)
    class ConvergenceApplied:
        context_id: str
        cache_key: str
        task_goal: str
        shards: list[dict[str, Any]]
        pipeline_result: PipelineExecutionResult
        execution_context: PipelineExecutionContext

    async def revise(
        self,
        context: dict[str, Any],
        feedback: dict[str, Any] | str | list[str] | None = None,
    ) -> PipelineExecutionResult:
        if feedback is None:
            return await self.run(context)

        feedback_dict: dict[str, Any]
        if isinstance(feedback, str):
            feedback_dict = {"message": feedback}
        elif isinstance(feedback, list):
            feedback_dict = {"messages": feedback}
        else:
            feedback_dict = feedback

        self.logger.info(
            "Revising pipeline with feedback",
            extra={
                "context": {
                    "feedback": feedback_dict,
                    "stage": "revision",
                }
            },
        )

        updated_context = context.copy()
        updated_context["feedback"] = feedback_dict
        return await self.run(updated_context)

    def set_progress_callback(
        self,
        callback: Callable[[str, float, float], Any],
    ) -> None:
        self.progress_callback = callback
        self.logger.debug(
            "Progress callback set",
            extra={"context": {"stage": "progress_setup"}},
        )
        self.logger_manager.log_metric(
            "progress_callbacks_set",
            1,
            self._metric_type.COUNTER,
            tags={"stage": "progress_setup"},
        )

    async def run(self, context: dict[str, Any]) -> PipelineExecutionResult:
        preparation = await self.prepare_execution(context)
        if isinstance(preparation, (self.CachedExecution, self.FailedExecution)):
            return preparation.result

        iteration = await self.execute_iteration(preparation)
        if isinstance(iteration, self.FailedExecution):
            return iteration.result

        convergence = await self.apply_convergence(iteration)
        if isinstance(convergence, self.FailedExecution):
            return convergence.result

        return await self.finalize_or_abort(convergence)

    async def prepare_execution(
        self, context: dict[str, Any]
    ) -> CachedExecution | FailedExecution | PreparedExecution:
        return await prepare_execution_state(
            self,
            context,
            prepared_cls=self.PreparedExecution,
            cached_cls=self.CachedExecution,
            failed_cls=self.FailedExecution,
        )

    async def execute_iteration(
        self, preparation: PreparedExecution
    ) -> IterationResult | FailedExecution:
        return await execute_iteration_state(
            self,
            preparation,
            iteration_cls=self.IterationResult,
            failed_cls=self.FailedExecution,
        )

    async def apply_convergence(
        self, iteration: IterationResult
    ) -> ConvergenceApplied | FailedExecution:
        return await apply_convergence_result(
            self,
            iteration,
            convergence_cls=self.ConvergenceApplied,
            failed_cls=self.FailedExecution,
        )

    async def finalize_or_abort(
        self, convergence: ConvergenceApplied
    ) -> PipelineExecutionResult:
        return await finalize_execution_result(self, convergence)

    def _generate_cache_key(self, context: dict[str, Any]) -> str:
        context_str = str(
            sorted(
                {
                    k: v for k, v in context.items() if k not in ["timestamp", "nonce"]
                }.items()
            )
        )
        cache_key = hashlib.sha256(context_str.encode()).hexdigest()
        self.logger.debug(
            "Generated cache key",
            extra={
                "context": {
                    "cache_key": cache_key,
                    "stage": "cache_key_generation",
                }
            },
        )
        self.logger_manager.log_metric(
            "cache_keys_generated",
            1,
            self._metric_type.COUNTER,
            tags={"stage": "cache_key_generation"},
        )
        return cache_key

    def _notify_progress(self, step: str, progress: float, total: float) -> None:
        if self.progress_callback:
            task = asyncio.create_task(
                self._async_notify_progress(step, progress, total)
            )
            self._progress_tasks.append(task)
            self._progress_tasks = [t for t in self._progress_tasks if not t.done()]

    async def _async_notify_progress(
        self,
        step: str,
        progress: float,
        total: float,
    ) -> None:
        if self.progress_callback is None:
            raise RuntimeError("Progress callback is None")
        try:
            result = self.progress_callback(step, progress, total)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            await self.logger.async_log(
                "ERROR",
                f"Progress callback failed: {e!s}",
                context={
                    "step": step,
                    "error": str(e),
                    "stage": "progress_notification",
                },
            )

    async def _error_result(
        self,
        msg: str,
        context: dict[str, Any] | None = None,
        stage: str = "pipeline",
    ) -> PipelineExecutionResult:
        return await build_error_result(self, msg, context, stage=stage)
