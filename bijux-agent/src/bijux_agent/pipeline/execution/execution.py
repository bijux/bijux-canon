"""Execution helpers for the pipeline orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Any, Protocol, TypeAlias, cast

from bijux_agent.pipeline.agent_registry import determine_required_stages
from bijux_agent.pipeline.execution.io import PipelineIOMixin
from bijux_agent.pipeline.execution.shard_processing import process_shard, shard_input
from bijux_agent.pipeline.execution.telemetry import PipelineExecutionContext
from bijux_agent.pipeline.termination import ExecutionTerminationReason

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
    task_handler: Any

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
        context_id = context.get(
            "context_id",
            hashlib.sha256(str(sorted(context.items())).encode()).hexdigest(),
        )
        self.reset_telemetry()
        with self.logger.context(agent="Pipeline", context_id=context_id):
            self.logger.info(
                "Pipeline execution started",
                extra={
                    "context": {
                        "context_id": context_id,
                        "input_keys": list(context.keys()),
                        "task_goal": context.get("task_goal", "undefined"),
                    }
                },
            )

        pipeline_result: PipelineExecutionResult = {
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
        self.audit_trail = []
        self.revision_history = []

        cache_key = self._generate_cache_key(context)
        if self._cache is not None and cache_key in self._cache:
            self.logger.debug(
                "Returning cached pipeline result",
                extra={"context": {"cache_key": cache_key}},
            )
            cached_result = dict(self._cache[cache_key])
            cached_result["cache_hit"] = True
            self.logger_manager.log_metric(
                "pipeline_cache_hits",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "cache_check"},
            )
            return self.CachedExecution(cached_result)

        if not context or "task_goal" not in context:
            error_msg = (
                "Input context must provide 'task_goal' to define the task objective"
            )
            self.logger.error(
                error_msg,
                extra={"context": {"stage": "input_validation"}},
            )
            self.logger_manager.log_metric(
                "input_validation_errors",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "input_validation"},
            )
            error_result = await self._error_result(
                error_msg, context, "input_validation"
            )
            return self.FailedExecution(error_result)

        current_context = context.copy()
        task_goal = context["task_goal"].lower()

        required_stages = (
            self._stages if self._stages else determine_required_stages(self, task_goal)
        )
        self.logger.info(
            "Determined required stages for task",
            extra={
                "context": {
                    "task_goal": task_goal,
                    "required_stages": [stage["name"] for stage in required_stages],
                    "stage": "stage_configuration",
                }
            },
        )

        shards = await shard_input(self, current_context)
        return self.PreparedExecution(
            context_id=context_id,
            cache_key=cache_key,
            context=current_context,
            task_goal=task_goal,
            required_stages=required_stages,
            shards=shards,
            pipeline_result=pipeline_result,
            execution_context=execution_context,
        )

    async def execute_iteration(
        self, preparation: PreparedExecution
    ) -> IterationResult | FailedExecution:
        shard_results: list[ShardResult] = []
        for shard_idx, shard_context in enumerate(preparation.shards):
            self.logger.info(
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
                self,
                shard_context,
                shard_idx,
                len(preparation.shards),
                preparation.required_stages,
            )
            shard_results.append(shard_result)

            audit_trail = cast(
                list[dict[str, Any]], preparation.pipeline_result["audit_trail"]
            )
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
                self.logger.error(
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
                return self.FailedExecution(preparation.pipeline_result)

        hooks = cast(_ResultsHooks, self)
        merged_result = await hooks._merge_shard_results(
            shard_results, preparation.required_stages
        )
        preparation.pipeline_result["stages"] = merged_result["stages"]
        preparation.pipeline_result["final_status"] = merged_result["final_status"]

        final_result = await hooks._extract_final_result(
            merged_result["stages"], preparation.task_goal
        )
        preparation.pipeline_result["result"] = final_result

        return self.IterationResult(
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

    async def apply_convergence(
        self, iteration: IterationResult
    ) -> ConvergenceApplied | FailedExecution:
        hooks = cast(_ResultsHooks, self)
        validation_result = await hooks._validate_final_result(
            iteration.final_result, iteration.task_goal, iteration.context_id
        )
        if not validation_result["is_valid"]:
            self.logger.warning(
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
            return self.FailedExecution(iteration.pipeline_result)

        return self.ConvergenceApplied(
            context_id=iteration.context_id,
            cache_key=iteration.cache_key,
            task_goal=iteration.task_goal,
            shards=iteration.shards,
            pipeline_result=iteration.pipeline_result,
            execution_context=iteration.execution_context,
        )

    async def finalize_or_abort(
        self, convergence: ConvergenceApplied
    ) -> PipelineExecutionResult:
        convergence.pipeline_result["telemetry"] = (
            convergence.execution_context.finalize(len(convergence.shards))
        )
        duration = convergence.pipeline_result["telemetry"]["total_duration"]
        self.logger.info(
            "Pipeline execution completed",
            extra={
                "context": {
                    "total_duration": duration,
                    "shards_processed": len(convergence.shards),
                    "iterations": convergence.pipeline_result["telemetry"][
                        "iterations"
                    ],
                    "stages_executed": convergence.pipeline_result["telemetry"][
                        "stages_executed"
                    ],
                    "stage": "completion",
                }
            },
        )
        self.logger_manager.log_metric(
            "pipeline_executions",
            1,
            self._metric_type.COUNTER,
            tags={
                "status": (
                    "success"
                    if convergence.pipeline_result["final_status"]["success"]
                    else "failed"
                ),
                "stage": "completion",
            },
        )

        cache = self._cache
        if cache is not None:
            cache[convergence.cache_key] = convergence.pipeline_result
            self._cache = cache
            self.logger_manager.log_metric(
                "cache_stores",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "cache_store"},
            )

        self._persist_pipeline_result(
            convergence.pipeline_result, convergence.context_id
        )

        return convergence.pipeline_result

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
        result: PipelineExecutionResult = {
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
        await self.logger.async_log(
            "ERROR",
            msg,
            {
                "stage": stage,
                "context_id": (
                    context.get("context_id", "unknown") if context else "error"
                ),
            },
        )
        self.logger_manager.log_metric(
            "pipeline_errors",
            1,
            self._metric_type.COUNTER,
            tags={"stage": stage},
        )
        return result
