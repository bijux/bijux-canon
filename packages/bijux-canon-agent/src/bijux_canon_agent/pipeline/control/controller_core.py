"""Core state machine definitions for the canonical pipeline controller."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from bijux_canon_agent.enums import AgentType, DecisionOutcome
from bijux_canon_agent.pipeline.control.lifecycle import (
    LIFECYCLE_DETAILS,
    PIPELINE_LIFECYCLE,
    LifecycleInfo,
    PipelineLifecycle,
)
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict

TERMINAL_PHASES = (PipelineLifecycle.DONE, PipelineLifecycle.ABORTED)
REQUIRED_PREDECESSORS: dict[PipelineLifecycle, PipelineLifecycle] = {
    PipelineLifecycle.EXECUTE: PipelineLifecycle.PLAN,
    PipelineLifecycle.DONE: PipelineLifecycle.FINALIZE,
}


@dataclass
class PipelineControllerCore:
    """Low-level state tracking and transition guards for the pipeline."""

    phase: PipelineLifecycle = PipelineLifecycle.INIT
    context: dict[str, Any] = field(default_factory=dict)
    history: list[PipelineLifecycle] = field(
        default_factory=lambda: [PipelineLifecycle.INIT]
    )
    final_decision: DecisionOutcome | None = None
    final_confidence: float | None = None
    final_epistemic_verdict: EpistemicVerdict = EpistemicVerdict.CERTAIN

    def transition_to(self, target: PipelineLifecycle) -> None:
        """Transition the controller to the requested phase if allowed."""
        if self.phase == target:
            return
        self._require_predecessor(target)
        if target not in self._allowed_transitions():
            raise RuntimeError(
                f"Cannot transition from {self.phase.value} to {target.value}"
            )
        self.phase = target
        self._record_history(target)

    def _allowed_transitions(self) -> tuple[PipelineLifecycle, ...]:
        if self.phase == PipelineLifecycle.ABORTED:
            return (PipelineLifecycle.ABORTED,)
        if self.phase not in PIPELINE_LIFECYCLE:
            return (PipelineLifecycle.ABORTED,)
        transitions: list[PipelineLifecycle] = [PipelineLifecycle.ABORTED]
        next_phase = self._next_lifecycle_phase()
        if next_phase is not None:
            transitions.append(next_phase)
        return tuple(transitions)

    def _next_lifecycle_phase(self) -> PipelineLifecycle | None:
        current_index = PIPELINE_LIFECYCLE.index(self.phase)
        next_index = current_index + 1
        if next_index >= len(PIPELINE_LIFECYCLE):
            return None
        return PIPELINE_LIFECYCLE[next_index]

    def _require_predecessor(self, target: PipelineLifecycle) -> None:
        predecessor = REQUIRED_PREDECESSORS.get(target)
        if predecessor is None or self.phase == predecessor:
            return
        raise RuntimeError(
            f"Transitioning to {target.value} must follow {predecessor.value}"
        )

    def _record_history(self, target: PipelineLifecycle) -> None:
        if not self.history or self.history[-1] != target:
            self.history.append(target)

    def update_context(self, context_updates: Mapping[str, Any]) -> None:
        """Merge new values into the controller context."""
        self.context.update(context_updates)

    def _align_agent(self, agent_type: AgentType) -> None:
        """Ensure the requested agent type is allowed for the current phase."""
        info = self._lifecycle_info()
        if info.allowed_agents and agent_type not in info.allowed_agents:
            raise RuntimeError(
                f"Agent {agent_type.value} not allowed during {self.phase.value}"
            )

    def _lifecycle_info(self) -> LifecycleInfo:
        info = LIFECYCLE_DETAILS.get(self.phase)
        if info is None:
            raise RuntimeError(f"Unknown phase info for {self.phase}")
        return info

    @property
    def is_terminal(self) -> bool:
        """True once the controller has entered a terminal phase."""
        return self.phase in TERMINAL_PHASES
