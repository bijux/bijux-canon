"""BaseAgent module for Bijux Agent.

This module provides the BaseAgent abstract base class, which defines the core contract
for all agents in the bijux_agent system. It enforces async execution, feedback-driven
revision, and telemetry support, with schema and coverage reporting hooks for
pipeline orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Generic, final

from typing_extensions import TypeVar

from bijux_agent.agents.kernel.execution_kernel import AgentExecutionKernel
from bijux_agent.agents.kernel.lifecycle import LifecyclePhase
from bijux_agent.enums import AgentType, ExecutionMode, FailureMode
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.schema import AgentInput, AgentOutput
from bijux_agent.utilities.logger_manager import LoggerManager

InputT = TypeVar("InputT", bound=Mapping[str, Any])
OutputT = TypeVar("OutputT")


class BaseAgent(Generic[InputT, OutputT], ABC):
    """Abstract base class for all agents in the bijux_agent system.

    Core Principles:
    - Enforces explicit implementation of the core agent contract (`run`).
    - Provides a structured interface for output revision with feedback.
    - Supports async execution for compatibility with modern pipelines.
    - Offers schema and coverage reporting for orchestration and validation.
    - Includes telemetry and metadata for monitoring and pipeline integration.
    """

    # Lifecycle call graph: __init__ → _initialize → run → revise → fail → _cleanup.
    # Shared validation and error handling live inside AgentExecutionKernel.
    def __init__(self, config: dict[str, Any], logger_manager: LoggerManager):
        """Initialize the agent with configuration and logger manager.

        Args:
            config: Configuration dictionary for the agent.
            logger_manager: The LoggerManager instance for logging.
        """
        self.config = config
        self.logger_manager = logger_manager
        self.logger = logger_manager.get_logger()
        self.execution_kernel: AgentExecutionKernel[OutputT] = AgentExecutionKernel(
            self
        )
        self._initialize()

    def _initialize(self) -> None:
        """Hook for subclass initialization (e.g., resource setup).

        Default implementation is no-op. Subclasses may override to perform setup.
        """
        return None

    def _cleanup(self) -> None:
        """Hook for subclass cleanup (e.g., resource release).

        Default implementation is no-op. Subclasses may override to release resources.
        """
        return None

    @final
    async def run(self, context: AgentInput | dict[str, Any]) -> OutputT:
        """Execute the agent's core logic asynchronously (kernel-owned)."""
        validated = self.execution_kernel.validate_context(context, LifecyclePhase.RUN)
        normalized = self.execution_kernel.normalize_context(
            validated, LifecyclePhase.RUN
        )
        return await self._run_payload(normalized)

    @abstractmethod
    async def _run_payload(self, context: dict[str, Any]) -> OutputT:
        """Agent-specific logic for a normalized payload."""

    def validate_context(self, context: AgentInput | dict[str, Any]) -> AgentInput:
        """Validate context inputs via the execution kernel."""
        return self.execution_kernel.validate_context(context, LifecyclePhase.RUN)

    def _default_agent_type(self) -> AgentType:
        return AgentType.PLANNER

    def _default_execution_mode(self) -> ExecutionMode:
        return ExecutionMode.SYNC

    def validate_output(self, payload: dict[str, Any]) -> AgentOutput:
        return self.execution_kernel.validate_output(payload, LifecyclePhase.RUN)

    def _coerce_to_contract_output(self, validated: AgentOutput) -> AgentOutputSchema:
        """Convert internal AgentOutput to the shared contract schema."""
        payload: dict[str, Any] = validated.model_dump(exclude={"decision"})
        return AgentOutputSchema(**payload)

    @final
    def fail(
        self, reason: FailureMode, message: str, details: str | None = None
    ) -> None:
        self.execution_kernel.fail(reason, message, details, LifecyclePhase.FAIL)

    @final
    async def revise(
        self,
        context: AgentInput | dict[str, Any],
        feedback: dict[str, Any] | str | list[str] | None = None,
    ) -> OutputT:
        """Revise or correct the agent's output based on feedback.

        Default implementation reruns the agent if no feedback is provided. Subclasses
        should override to handle feedback explicitly.

        Args:
            context: Original input context for reprocessing.
            feedback: Optional feedback (string, dict, or list) from the pipeline or
                      other agents.

        Returns:
            A dictionary containing the revised agent output.

        Raises:
            NotImplementedError: If feedback is provided but not handled by the
                                 subclass.
        """
        return await self.execution_kernel.revise(
            context, feedback, LifecyclePhase.REVISE
        )

    def _revise_payload(
        self, feedback: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Allow agents to adjust inputs based on feedback."""
        updated = dict(context)
        updated["feedback"] = feedback
        return updated

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Default error payload shared by agents."""
        _ = extra
        return {
            "error": msg,
            "stage": stage,
            "input": context,
        }

    @classmethod
    def self_report_schema(cls) -> dict[str, Any]:
        """Describe the agent's output schema for validation, composition, and UI.

        Subclasses should override to provide a detailed schema.

        Returns:
            A dictionary describing the output schema (e.g., keys, types,
            constraints).
        """
        return {
            "error": "str (optional)",
            "warnings": "list[str] (optional)",
            "action_plan": "list[str] (optional, for feedback loop)",
        }

    @classmethod
    def coverage_report(cls, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Describe the parts of the context/input this agent consumes or modifies.

        Subclasses may use the context to report dynamic coverage.

        Args:
            context: Optional input context to analyze for dynamic coverage.

        Returns:
            A dictionary detailing consumed and modified context keys.
        """
        _ = context  # Mark as intentionally unused
        return {"consumes": [], "modifies": [], "produces": []}

    @property
    def id(self) -> str:
        """A unique identifier for the agent, used for audit and provenance."""
        return self.__class__.__name__

    @property
    def version(self) -> str:
        """Human-readable version for audit and reporting."""
        return "0.2.0"

    @property
    def name(self) -> str:
        """Human-readable name for display in dashboards and logs."""
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """Short description for pipeline orchestration, dashboards, etc."""
        return self.__doc__ or self.__class__.__name__

    @property
    def capabilities(self) -> list[str]:
        """List of capabilities this agent supports: file_reading, summarization."""
        return []

    async def get_telemetry(self) -> dict[str, Any]:
        """Retrieve telemetry metrics for the agent.

        Subclasses should override to provide specific metrics.

        Returns:
            A dictionary of telemetry metrics.
        """
        return {}

    def reset_telemetry(self) -> None:
        """Reset telemetry counters; no-op by default."""
        return None

    async def shutdown(self) -> None:
        """Perform cleanup tasks when the agent is shutting down.

        Subclasses can override to release resources.
        """
        return None
