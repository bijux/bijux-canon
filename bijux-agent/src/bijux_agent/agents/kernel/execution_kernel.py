"""Execution kernel for agents encapsulating shared validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from bijux_agent.agents.kernel.lifecycle import LifecyclePhase
from bijux_agent.enums import AgentStatus, FailureMode
from bijux_agent.schema import AgentInput, AgentOutput

OutputT = TypeVar("OutputT")

if TYPE_CHECKING:
    from bijux_agent.agents.base import BaseAgent


class AgentExecutionKernel(Generic[OutputT]):
    """Shared execution helpers (validation, error handling) for agents."""

    def __init__(self, agent: BaseAgent[Any, OutputT]) -> None:
        self._agent = agent
        self._seen_run = False
        self._seen_fail = False

    def _record_phase(self, phase: LifecyclePhase) -> None:
        if phase is LifecyclePhase.RUN and self._seen_fail:
            raise RuntimeError("Lifecycle violation: RUN cannot occur after FAIL")
        if phase is LifecyclePhase.REVISE and not self._seen_run:
            raise RuntimeError("Lifecycle violation: REVISE requires prior RUN")
        if phase is LifecyclePhase.RUN:
            self._seen_run = True
        if phase is LifecyclePhase.FAIL:
            self._seen_fail = True

    @staticmethod
    def _resolve_phase(
        phase: LifecyclePhase | None, default: LifecyclePhase
    ) -> LifecyclePhase:
        return phase or default

    def normalize_context(
        self,
        context: AgentInput | dict[str, Any],
        phase: LifecyclePhase | None = None,
    ) -> dict[str, Any]:
        """Normalize input to the prior dict shape used by agents."""
        _ = phase
        if isinstance(context, AgentInput):
            normalized = {
                "task_goal": context.task_goal,
                "payload": dict(context.payload),
                "context_id": context.context_id,
                "metadata": dict(context.metadata),
                "agent_type": context.agent_type,
                "execution_mode": context.execution_mode,
            }
            normalized.update(dict(context.payload))
            return normalized
        return dict(context)

    def validate_context(
        self,
        context: AgentInput | dict[str, Any],
        phase: LifecyclePhase | None = None,
    ) -> AgentInput:
        """Ensure the context satisfies minimal requirements."""
        self._record_phase(self._resolve_phase(phase, LifecyclePhase.RUN))
        if isinstance(context, AgentInput):
            return context
        try:
            task_goal = context["task_goal"]
            context_id = context["context_id"]
        except KeyError as exc:
            raise exc
        payload = dict(context.get("payload", {}))
        for key, value in context.items():
            if key not in {
                "task_goal",
                "payload",
                "context_id",
                "metadata",
                "agent_type",
                "execution_mode",
            }:
                payload.setdefault(key, value)
        return AgentInput(
            task_goal=str(task_goal),
            payload=payload,
            context_id=str(context_id),
            metadata=dict(context.get("metadata", {})),
            agent_type=context.get("agent_type", self._agent._default_agent_type()),
            execution_mode=context.get(
                "execution_mode", self._agent._default_execution_mode()
            ),
        )

    def validate_output(
        self, payload: dict[str, Any], phase: LifecyclePhase | None = None
    ) -> AgentOutput:
        """Validate output payload confidences and set agent status."""
        self._record_phase(self._resolve_phase(phase, LifecyclePhase.RUN))
        output = AgentOutput(**payload)
        if not (0.0 <= output.confidence <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")
        self._agent.status = AgentStatus.SUCCESS
        return output

    def fail(
        self,
        reason: FailureMode,
        message: str,
        details: str | None,
        phase: LifecyclePhase | None = None,
    ) -> None:
        """Centralized failure path for agents."""
        self._record_phase(self._resolve_phase(phase, LifecyclePhase.FAIL))
        self._agent.status = AgentStatus.FAILED
        detail_text = f" {details}" if details else ""
        raise RuntimeError(f"{reason.value}: {message}{detail_text}")

    async def revise(
        self,
        context: AgentInput | dict[str, Any],
        feedback: dict[str, Any] | str | list[str] | None,
        phase: LifecyclePhase | None = None,
    ) -> OutputT:
        """Centralized revise path that preserves control flow."""
        self._record_phase(self._resolve_phase(phase, LifecyclePhase.REVISE))
        if feedback is None:
            return await self._agent.run(context)
        if isinstance(feedback, str):
            feedback_dict = {"message": feedback}
        elif isinstance(feedback, list):
            feedback_dict = {"messages": feedback}
        else:
            feedback_dict = feedback
        context_dict = self.normalize_context(context)
        updated_context = self._agent._revise_payload(feedback_dict, context_dict)
        return await self._agent.run(updated_context)

    async def error_result(
        self,
        msg: str,
        context: AgentInput | dict[str, Any] | None,
        stage: str,
        extra: dict[str, Any] | None = None,
        phase: LifecyclePhase | None = None,
    ) -> dict[str, Any]:
        """Build a standardized error result and emit async logs."""
        self._record_phase(self._resolve_phase(phase, LifecyclePhase.FAIL))
        context_dict = self.normalize_context(context or {})
        payload = self._agent.error_payload(msg, context_dict, stage, extra)
        log_context = {
            "stage": stage,
            "context_id": context_dict.get("context_id", "error"),
        }
        if extra:
            log_context.update(extra)
        await self._agent.logger.async_log(
            "ERROR",
            msg,
            log_context,
        )
        return payload

    async def get_telemetry(self) -> dict[str, Any]:
        """Kernel-owned telemetry access with minimal indirection."""
        return await self._agent.get_telemetry()
