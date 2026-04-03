"""Runtime helpers layered on top of the pipeline controller core."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_agent.enums import DecisionOutcome
from bijux_canon_agent.pipeline.control.controller_core import PipelineControllerCore
from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle
from bijux_canon_agent.pipeline.control.stop_conditions import StopReason
from bijux_canon_agent.pipeline.epistemic import EpistemicVerdict
from bijux_canon_agent.pipeline.results.outcome import PipelineResult
from bijux_canon_agent.tracing.trace import RunTrace


@dataclass
class PipelineController(PipelineControllerCore):
    """Controller that applies runtime stop/retry/finalization behavior."""

    stop_reason: StopReason | None = None
    stop_details: str | None = None

    def record_outcome(
        self,
        decision: DecisionOutcome,
        confidence: float,
        epistemic_verdict: EpistemicVerdict | None = None,
    ) -> None:
        """Capture the final decision metadata."""
        self.final_decision = decision
        self.final_confidence = confidence
        if epistemic_verdict is not None:
            self.final_epistemic_verdict = epistemic_verdict

    def request_stop(
        self,
        reason: StopReason,
        details: str | None = None,
    ) -> None:
        """Request the controller to transition into an abort path."""
        self.stop_reason = reason
        self.stop_details = details
        self.final_epistemic_verdict = EpistemicVerdict.UNCERTAIN
        if reason == StopReason.EPISTEMIC_FAILURE:
            self.final_decision = DecisionOutcome.VETO
        if self.phase != PipelineLifecycle.ABORTED:
            self.transition_to(PipelineLifecycle.ABORTED)

    def should_stop(self) -> bool:
        """Return True when an explicit stop reason exists."""
        return self.stop_reason is not None

    def finalize(self, trace: RunTrace) -> PipelineResult:
        """Return the canonical outcome once the run completes."""
        if self.should_stop():
            self.transition_to(PipelineLifecycle.ABORTED)
        else:
            self.transition_to(PipelineLifecycle.DONE)
        return PipelineResult.from_trace(trace)
