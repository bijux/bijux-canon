"""Lifecycle helpers for the Pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from bijux_agent.config.defaults import PIPELINE_DEFAULTS
from bijux_agent.pipeline.agent_registry import (
    load_critique_agent,
    load_file_reader_agent,
    load_summarizer_agent,
    load_task_handler_agent,
    load_universal_file_reader,
    load_validator_agent,
)

PipelineExecutionResult: TypeAlias = dict[str, Any]

if TYPE_CHECKING:
    from bijux_agent.agents.critique import CritiqueAgent
    from bijux_agent.agents.file_reader import FileReaderAgent
    from bijux_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )
    from bijux_agent.agents.summarizer import SummarizerAgent
    from bijux_agent.agents.taskhandler import TaskHandlerAgent
    from bijux_agent.agents.validator import ValidatorAgent
    from bijux_agent.utilities.logger_manager import LoggerManager

_metric_type_cls: type[Any] | None = None


def _get_metric_type() -> type[Any]:
    global _metric_type_cls
    if _metric_type_cls is None:
        from bijux_agent.utilities.logger_manager import MetricType as _MetricType

        _metric_type_cls = _MetricType
    return _metric_type_cls


class PipelineLifecycleMixin:
    """Shared pipeline lifecycle hooks (init, telemetry, shutdown)."""

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        task_handler_agent: TaskHandlerAgent | None = None,
        file_reader_agent: FileReaderAgent | None = None,
        summarizer_agent: SummarizerAgent | None = None,
        validator_agent: ValidatorAgent | None = None,
        critique_agent: CritiqueAgent | None = None,
        universal_agent: UniversalFileReader | None = None,
        max_retries: int | None = None,
        chunk_size: int | None = None,
        shard_threshold: int | None = None,
        max_iterations: int | None = None,
        concurrency_limit: int | None = None,
        stage_timeout: float | None = None,
        retry_delay: float | None = None,
        quality_threshold: float | None = None,
        results_dir: str = "../bijux-agent_test/results",
    ) -> None:
        self.logger_manager = logger_manager
        self.logger = logger_manager.get_logger()
        self._metric_type = _get_metric_type()
        self._cache: dict[str, PipelineExecutionResult] | None = (
            {} if config.get("enable_cache", True) else None
        )
        self._custom_ensemble_strategies: dict[
            str, Callable[[list[dict[str, Any]], list[float]], dict[str, Any]]
        ] = {}
        self.feedback_rules: dict[str, Any] = config.get("pipeline", {}).get(
            "feedback_rules", {}
        )
        self.progress_callback: Callable[[str, float, float], None] | None = None
        self.audit_trail: list[dict[str, Any]] = []
        self.revision_history: list[dict[str, Any]] = []
        self._stages: list[dict[str, Any]] = []
        self._progress_tasks: list[asyncio.Task[Any]] = []

        pipeline_config = config.get("pipeline", {})
        pipeline_parameters = pipeline_config.get("parameters", {})
        pipeline_policy = pipeline_config.get("policy", {})
        self.policy = pipeline_policy

        def _resolve(key: str, override: Any | None) -> Any:
            if override is not None:
                return override
            if key in pipeline_parameters:
                return pipeline_parameters[key]
            return config.get(key, PIPELINE_DEFAULTS[key])

        self.max_retries: int = int(_resolve("max_retries", max_retries))
        self.chunk_size: int = int(_resolve("chunk_size", chunk_size))
        self.shard_threshold: int = int(_resolve("shard_threshold", shard_threshold))
        self.max_iterations: int = int(_resolve("max_iterations", max_iterations))
        self.concurrency_limit: int = int(
            _resolve("concurrency_limit", concurrency_limit)
        )
        self.stage_timeout: float = float(_resolve("stage_timeout", stage_timeout))
        self.retry_delay: float = float(_resolve("retry_delay", retry_delay))
        self.quality_threshold: float = float(
            _resolve("quality_threshold", quality_threshold)
        )
        if not self.policy.get("retry_allowed", True) and self.max_retries > 0:
            raise RuntimeError("Retry policy forbids retries but max_retries > 0")

        self.results_dir: Path = Path(results_dir).resolve()
        self.results_dir.mkdir(parents=True, exist_ok=True)

        universal_cls = load_universal_file_reader()
        self.universal_agent: UniversalFileReader = universal_agent or universal_cls(
            config
        )
        file_reader_cls = load_file_reader_agent()
        self.file_reader: FileReaderAgent = file_reader_agent or file_reader_cls(
            config=config,
            logger_manager=logger_manager,
        )
        summarizer_cls = load_summarizer_agent()
        self.summarizer: SummarizerAgent = summarizer_agent or summarizer_cls(
            config=config,
            logger_manager=logger_manager,
        )
        validator_cls = load_validator_agent()
        self.validator: ValidatorAgent = validator_agent or validator_cls(
            config=config,
            logger_manager=logger_manager,
        )
        critique_cls = load_critique_agent()
        self.critique: CritiqueAgent = critique_agent or critique_cls(
            config=config,
            logger_manager=logger_manager,
        )
        task_handler_cls = load_task_handler_agent()
        self.task_handler: TaskHandlerAgent = task_handler_agent or task_handler_cls(
            config=config,
            logger_manager=logger_manager,
        )

        self.logger.info(
            "Pipeline initialized",
            extra={
                "context": {
                    "max_retries": self.max_retries,
                    "chunk_size": self.chunk_size,
                    "shard_threshold": self.shard_threshold,
                    "max_iterations": self.max_iterations,
                    "concurrency_limit": self.concurrency_limit,
                    "stage_timeout": self.stage_timeout,
                    "retry_delay": self.retry_delay,
                    "quality_threshold": self.quality_threshold,
                }
            },
        )

    def _initialize(self) -> None:
        return None

    def _cleanup(self) -> None:
        return None

    def flush_logs(self) -> None:
        try:
            self.logger_manager.flush()
            self.logger.debug(
                "Logs flushed",
                extra={"context": {"stage": "log_flush"}},
            )
            self.logger_manager.log_metric(
                "log_flush",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "log_flush"},
            )
        except Exception as e:
            self.logger.error(
                "Failed to flush logs",
                extra={"context": {"error": str(e), "stage": "log_flush"}},
            )

    async def get_telemetry(self) -> dict[str, dict[str, Any]]:
        try:
            pipeline_metrics = self.logger_manager.get_metrics()
            agent_metrics = {
                "FileReaderAgent": (
                    await self.file_reader.execution_kernel.get_telemetry()
                    if self.file_reader
                    else {}
                ),
                "SummarizerAgent": (
                    await self.summarizer.execution_kernel.get_telemetry()
                    if self.summarizer
                    else {}
                ),
                "ValidatorAgent": (
                    await self.validator.execution_kernel.get_telemetry()
                    if self.validator
                    else {}
                ),
                "CritiqueAgent": (
                    await self.critique.execution_kernel.get_telemetry()
                    if self.critique
                    else {}
                ),
                "TaskHandlerAgent": (
                    await self.task_handler.execution_kernel.get_telemetry()
                    if self.task_handler
                    else {}
                ),
            }
            self.logger.debug(
                "Telemetry retrieved for pipeline and agents",
                extra={
                    "context": {
                        "metric_keys": list(pipeline_metrics.keys()),
                        "agent_metrics_keys": list(agent_metrics.keys()),
                        "stage": "telemetry",
                    }
                },
            )
            self.logger_manager.log_metric(
                "telemetry_retrieved",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "telemetry"},
            )
            return {"pipeline": pipeline_metrics, "agents": agent_metrics}
        except Exception as e:
            self.logger.error(
                "Failed to retrieve telemetry",
                extra={"context": {"error": str(e), "stage": "telemetry"}},
            )
            return {}

    def reset_telemetry(self) -> None:
        try:
            self.logger_manager.reset_metrics()
            for agent in [
                self.file_reader,
                self.summarizer,
                self.validator,
                self.critique,
                self.task_handler,
            ]:
                if agent and hasattr(agent, "reset_telemetry"):
                    agent.reset_telemetry()
            self.logger.debug(
                "Telemetry metrics reset for pipeline and agents",
                extra={"context": {"stage": "reset_telemetry"}},
            )
            self.logger_manager.log_metric(
                "metrics_reset",
                1,
                self._metric_type.COUNTER,
                tags={"stage": "reset_telemetry"},
            )
        except Exception as e:
            self.logger.error(
                "Failed to reset telemetry",
                extra={"context": {"error": str(e), "stage": "reset_telemetry"}},
            )

    async def shutdown(self) -> None:
        self.logger.info(
            "Shutting down pipeline",
            extra={"context": {"stage": "shutdown"}},
        )
        for agent in [
            self.file_reader,
            self.summarizer,
            self.validator,
            self.critique,
            self.task_handler,
        ]:
            if agent and hasattr(agent, "shutdown"):
                await agent.shutdown()
        if self._progress_tasks:
            await asyncio.gather(*self._progress_tasks, return_exceptions=True)
            self._progress_tasks.clear()
        self.flush_logs()
        self.logger.info(
            "Pipeline shutdown completed",
            extra={"context": {"stage": "shutdown"}},
        )
