"""Experimental pipeline facade; prefer the canonical AuditableDocPipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_canon_agent.pipeline.execution.execution import PipelineExecutionMixin
from bijux_canon_agent.pipeline.execution.lifecycle import PipelineLifecycleMixin
from bijux_canon_agent.pipeline.orchestration import PipelineOrchestrationMixin
from bijux_canon_agent.pipeline.results.results import PipelineResultsMixin

if TYPE_CHECKING:
    from bijux_canon_agent.agents.critique import CritiqueAgent
    from bijux_canon_agent.agents.file_reader import FileReaderAgent
    from bijux_canon_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )
    from bijux_canon_agent.agents.summarizer import SummarizerAgent
    from bijux_canon_agent.agents.stage_runner import StageRunnerAgent
    from bijux_canon_agent.agents.validator import ValidatorAgent
    from bijux_canon_agent.observability.logging import LoggerManager


CANONICAL_PIPELINE_PATH = "bijux_canon_agent.pipeline.canonical.AuditableDocPipeline"


class Pipeline(
    PipelineLifecycleMixin,
    PipelineOrchestrationMixin,
    PipelineExecutionMixin,
    PipelineResultsMixin,
):
    """Orchestrates multi-agent task execution while keeping deterministic state."""

    def __init__(
        self,
        config: dict[str, Any],
        logger_manager: LoggerManager,
        stage_runner_agent: StageRunnerAgent | None = None,
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
        pipeline_path = f"{self.__class__.__module__}.{self.__class__.__name__}"
        if pipeline_path != CANONICAL_PIPELINE_PATH:
            raise RuntimeError(
                "Only the AuditableDocPipeline is supported in production. "
                "Instantiate bijux_canon_agent.pipeline.canonical.AuditableDocPipeline "
                "instead."
            )
        PipelineLifecycleMixin.__init__(
            self,
            config,
            logger_manager,
            stage_runner_agent,
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
            results_dir
            if results_dir is not None
            else "../bijux-canon-agent_test/results",
        )
