"""Agent loaders and stage resolution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_agent.pipeline.stages import (
    build_stage_definitions,
    filter_stages_for_goal,
)

if TYPE_CHECKING:
    from bijux_agent.agents.critique import CritiqueAgent
    from bijux_agent.agents.file_reader import FileReaderAgent
    from bijux_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )
    from bijux_agent.agents.summarizer import SummarizerAgent
    from bijux_agent.agents.taskhandler import TaskHandlerAgent
    from bijux_agent.agents.validator import ValidatorAgent


def load_task_handler_agent() -> type[TaskHandlerAgent]:
    from bijux_agent.agents.taskhandler import TaskHandlerAgent

    return TaskHandlerAgent


def load_file_reader_agent() -> type[FileReaderAgent]:
    from bijux_agent.agents.file_reader import FileReaderAgent

    return FileReaderAgent


def load_summarizer_agent() -> type[SummarizerAgent]:
    from bijux_agent.agents.summarizer import SummarizerAgent

    return SummarizerAgent


def load_validator_agent() -> type[ValidatorAgent]:
    from bijux_agent.agents.validator import ValidatorAgent

    return ValidatorAgent


def load_critique_agent() -> type[CritiqueAgent]:
    from bijux_agent.agents.critique import CritiqueAgent

    return CritiqueAgent


def load_universal_file_reader() -> type[UniversalFileReader]:
    from bijux_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )

    return UniversalFileReader


def determine_required_stages(pipeline: Any, task_goal: str) -> list[dict[str, Any]]:
    """Return the set of required stages for the given task goal."""

    stage_defs = build_stage_definitions(pipeline)
    return filter_stages_for_goal(task_goal, pipeline, stage_defs)
