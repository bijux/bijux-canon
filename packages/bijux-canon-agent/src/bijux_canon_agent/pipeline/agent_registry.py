"""Agent loaders and execution-plan resolution helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bijux_canon_agent.pipeline.execution_plan import (
    build_execution_plan,
    filter_execution_plan_for_goal,
)

if TYPE_CHECKING:
    from bijux_canon_agent.agents.critique import CritiqueAgent
    from bijux_canon_agent.agents.file_reader import FileReaderAgent
    from bijux_canon_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )
    from bijux_canon_agent.agents.summarizer import SummarizerAgent
    from bijux_canon_agent.agents.workflow_executor import WorkflowExecutorAgent
    from bijux_canon_agent.agents.validator import ValidatorAgent


def load_workflow_executor_agent() -> type[WorkflowExecutorAgent]:
    from bijux_canon_agent.agents.workflow_executor import WorkflowExecutorAgent

    return WorkflowExecutorAgent


def load_file_reader_agent() -> type[FileReaderAgent]:
    from bijux_canon_agent.agents.file_reader import FileReaderAgent

    return FileReaderAgent


def load_summarizer_agent() -> type[SummarizerAgent]:
    from bijux_canon_agent.agents.summarizer import SummarizerAgent

    return SummarizerAgent


def load_validator_agent() -> type[ValidatorAgent]:
    from bijux_canon_agent.agents.validator import ValidatorAgent

    return ValidatorAgent


def load_critique_agent() -> type[CritiqueAgent]:
    from bijux_canon_agent.agents.critique import CritiqueAgent

    return CritiqueAgent


def load_universal_file_reader() -> type[UniversalFileReader]:
    from bijux_canon_agent.agents.file_reader.capabilities.universal_file_reader_core import (
        UniversalFileReader,
    )

    return UniversalFileReader


def determine_execution_plan(pipeline: Any, task_goal: str) -> list[dict[str, Any]]:
    """Return the execution plan for the given task goal."""

    execution_plan = build_execution_plan(pipeline)
    return filter_execution_plan_for_goal(task_goal, execution_plan)
