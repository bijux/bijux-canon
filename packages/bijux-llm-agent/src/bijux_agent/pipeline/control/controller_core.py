"""Core state machine definitions for the canonical pipeline controller."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.pipeline.control.phases import (
    PHASE_DETAILS,
    PHASE_SEQUENCE,
    PipelinePhase,
)
from bijux_agent.pipeline.epistemic import EpistemicVerdict


@dataclass
class PipelineControllerCore:
    """Low-level state tracking and transition guards for the pipeline."""

    phase: PipelinePhase = PipelinePhase.INIT
    context: dict[str, Any] = field(default_factory=dict)
    history: list[PipelinePhase] = field(default_factory=lambda: [PipelinePhase.INIT])
    final_decision: DecisionOutcome | None = None
    final_confidence: float | None = None
    final_epistemic_verdict: EpistemicVerdict = EpistemicVerdict.CERTAIN

    def transition_to(self, target: PipelinePhase) -> None:
        """Transition the controller to the requested phase if allowed."""
        if self.phase == target:
            return
        if target == PipelinePhase.EXECUTE and self.phase != PipelinePhase.PLAN:
            raise RuntimeError("Transitioning to EXECUTE must follow PLAN")
        if target == PipelinePhase.DONE and self.phase != PipelinePhase.FINALIZE:
            raise RuntimeError("Transitioning to DONE must follow FINALIZE")
        allowed = self._allowed_transitions()
        if target not in allowed:
            raise RuntimeError(
                f"Cannot transition from {self.phase.value} to {target.value}"
            )
        self.phase = target
        if not self.history or self.history[-1] != target:
            self.history.append(target)

    def _allowed_transitions(self) -> tuple[PipelinePhase, ...]:
        if self.phase == PipelinePhase.ABORTED:
            return (PipelinePhase.ABORTED,)
        if self.phase not in PHASE_SEQUENCE:
            return (PipelinePhase.ABORTED,)
        current_index = PHASE_SEQUENCE.index(self.phase)
        next_index = current_index + 1
        transitions: list[PipelinePhase] = [PipelinePhase.ABORTED]
        if next_index < len(PHASE_SEQUENCE):
            transitions.append(PHASE_SEQUENCE[next_index])
        return tuple(transitions)

    def update_context(self, context_updates: Mapping[str, Any]) -> None:
        """Merge new values into the controller context."""
        self.context.update(context_updates)

    def _align_agent(self, agent_type: AgentType) -> None:
        """Ensure the requested agent type is allowed for the current phase."""
        info = PHASE_DETAILS.get(self.phase)
        if not info:
            raise RuntimeError(f"Unknown phase info for {self.phase}")
        if info.allowed_agents and agent_type not in info.allowed_agents:
            raise RuntimeError(
                f"Agent {agent_type.value} not allowed during {self.phase.value}"
            )

    @property
    def is_terminal(self) -> bool:
        """True once the controller has entered a terminal phase."""
        return self.phase in (PipelinePhase.DONE, PipelinePhase.ABORTED)
