"""Canonical pipeline entrypoint for the auditable document workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bijux_agent.agents.file_reader import FileReaderAgent
from bijux_agent.pipeline.pipeline import Pipeline

if TYPE_CHECKING:
    from bijux_agent.agents.critique import CritiqueAgent
    from bijux_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )
    from bijux_agent.agents.summarizer import SummarizerAgent
    from bijux_agent.agents.taskhandler import TaskHandlerAgent
    from bijux_agent.agents.validator import ValidatorAgent
    from bijux_agent.utilities.logger_manager import LoggerManager


class AuditableDocPipeline(Pipeline):
    """Production pipeline that ships with a fixed, auditable configuration."""

    NAME = "auditable-doc-pipeline"

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
        results_dir: str | None = None,
    ) -> None:
        if file_reader_agent is not None and not isinstance(
            file_reader_agent, FileReaderAgent
        ):
            raise TypeError(
                "file_reader_agent must be an instance of FileReaderAgent or None"
            )
        super().__init__(
            config,
            logger_manager,
            task_handler_agent,
            file_reader_agent,
            summarizer_agent,
            validator_agent,
            critique_agent,
            universal_agent,
            max_retries,
            chunk_size,
            shard_threshold,
            max_iterations,
            concurrency_limit,
            stage_timeout,
            retry_delay,
            quality_threshold,
            results_dir,
        )

    # Override pipeline extension points to enforce the canonical build.
    def add_stage(
        self,
        name: str,
        agent: Any,
        weight: float | None = None,
        position: int | None = None,
        dependencies: list[str] | None = None,
        condition: Callable[[dict[str, Any]], bool] | None = None,
        timeout: float | None = None,
        output_key: str | None = None,
    ) -> None:
        raise RuntimeError(
            "Dynamic stage composition is disabled for the auditable doc pipeline."
        )

    def register_ensemble_strategy(
        self,
        strategy_name: str,
        strategy: Callable[[list[dict[str, Any]], list[float]], dict[str, Any]],
    ) -> None:
        raise RuntimeError(
            "Custom ensemble strategies are not supported by the "
            "auditable doc pipeline."
        )
