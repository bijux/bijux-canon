"""Core state machine definitions for the canonical pipeline controller."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from bijux_canon_agent.enums import AgentType, DecisionOutcome
from bijux_canon_agent.pipeline.control.lifecycle import (
    LIFECYCLE_DETAILS,
    PIPELINE_LIFECYCLE,
    PipelineLifecycle,
)
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict


@dataclass
class PipelineControllerCore:
    """Low-level state tracking and transition guards for the pipeline."""

    phase: PipelineLifecycle = PipelineLifecycle.INIT
    context: dict[str, Any] = field(default_factory=dict)
    history: list[PipelineLifecycle] = field(default_factory=lambda: [PipelineLifecycle.INIT])
    final_decision: DecisionOutcome | None = None
    final_confidence: float | None = None
    final_epistemic_verdict: EpistemicVerdict = EpistemicVerdict.CERTAIN

    def transition_to(self, target: PipelineLifecycle) -> None:
        """Transition the controller to the requested phase if allowed."""
        if self.phase == target:
            return
        if target == PipelineLifecycle.EXECUTE and self.phase != PipelineLifecycle.PLAN:
            raise RuntimeError("Transitioning to EXECUTE must follow PLAN")
        if target == PipelineLifecycle.DONE and self.phase != PipelineLifecycle.FINALIZE:
            raise RuntimeError("Transitioning to DONE must follow FINALIZE")
        allowed = self._allowed_transitions()
        if target not in allowed:
            raise RuntimeError(
                f"Cannot transition from {self.phase.value} to {target.value}"
            )
        self.phase = target
        if not self.history or self.history[-1] != target:
            self.history.append(target)

    def _allowed_transitions(self) -> tuple[PipelineLifecycle, ...]:
        if self.phase == PipelineLifecycle.ABORTED:
            return (PipelineLifecycle.ABORTED,)
        if self.phase not in PIPELINE_LIFECYCLE:
            return (PipelineLifecycle.ABORTED,)
        current_index = PIPELINE_LIFECYCLE.index(self.phase)
        next_index = current_index + 1
        transitions: list[PipelineLifecycle] = [PipelineLifecycle.ABORTED]
        if next_index < len(PIPELINE_LIFECYCLE):
            transitions.append(PIPELINE_LIFECYCLE[next_index])
        return tuple(transitions)

    def update_context(self, context_updates: Mapping[str, Any]) -> None:
        """Merge new values into the controller context."""
        self.context.update(context_updates)

    def _align_agent(self, agent_type: AgentType) -> None:
        """Ensure the requested agent type is allowed for the current phase."""
        info = LIFECYCLE_DETAILS.get(self.phase)
        if not info:
            raise RuntimeError(f"Unknown phase info for {self.phase}")
        if info.allowed_agents and agent_type not in info.allowed_agents:
            raise RuntimeError(
                f"Agent {agent_type.value} not allowed during {self.phase.value}"
            )

    @property
    def is_terminal(self) -> bool:
        """True once the controller has entered a terminal phase."""
        return self.phase in (PipelineLifecycle.DONE, PipelineLifecycle.ABORTED)
