"""Enum-driven orchestrator state machine."""

from __future__ import annotations

from dataclasses import dataclass, field

from bijux_agent.enums import PipelineState


@dataclass
class OrchestratorStateMachine:
    state: PipelineState = PipelineState.INIT
    _transitions: dict[PipelineState, tuple[PipelineState, ...]] = field(init=False)

    def __post_init__(self) -> None:
        self._transitions = {
            PipelineState.INIT: (PipelineState.RUNNING,),
            PipelineState.RUNNING: (PipelineState.JUDGING, PipelineState.ABORTED),
            PipelineState.JUDGING: (PipelineState.VERIFIED,),
            PipelineState.VERIFIED: (PipelineState.DONE, PipelineState.ABORTED),
            PipelineState.DONE: (),
            PipelineState.ABORTED: (),
        }

    def transition_to(self, target: PipelineState) -> None:
        """Advance to the requested state if the transition is allowed."""
        allowed = self._transitions.get(self.state, ())
        if target not in allowed:
            raise RuntimeError(
                f"Invalid transition {self.state.value} -> {target.value}"
            )
        self.state = target

    def abort(self) -> None:
        """Abort the current run when the abort transition is permitted."""
        if PipelineState.ABORTED not in self._transitions.get(
            self.state, ()
        ):  # pragma: no branch
            raise RuntimeError(f"Cannot abort from state {self.state.value}")
        self.state = PipelineState.ABORTED
