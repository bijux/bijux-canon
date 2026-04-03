"""Structured payloads describing pipeline completion details."""

from __future__ import annotations

from enum import Enum

from pydantic import ConfigDict, Field

from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.schema.base import TypedBaseModel
from bijux_agent.tracing.trace import ModelMetadata, RunTrace
from bijux_agent.utilities.final import final_class


class PipelineStatus(str, Enum):
    DONE = "DONE"
    ABORTED = "ABORTED"


@final_class
class PipelineResult(TypedBaseModel):
    """Canonical structure describing the final pipeline outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: PipelineStatus
    decision: DecisionOutcome
    epistemic_verdict: EpistemicVerdict
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Normalized confidence [0,1]"
    )
    stop_reason: StopReason | None = None
    model_metadata: ModelMetadata

    @classmethod
    def from_trace(cls, trace: RunTrace) -> PipelineResult:
        """Reconstitute a final outcome payload from a recorded trace."""

        status_str = (trace.status or "completed").lower()
        status = (
            PipelineStatus.ABORTED if status_str == "aborted" else PipelineStatus.DONE
        )

        final_entry = trace.entries[-1] if trace.entries else None
        confidence = 0.0
        decision = DecisionOutcome.APPROVE
        epistemic = EpistemicVerdict.CERTAIN
        stop_reason = None

        if final_entry:
            output = final_entry.output or {}
            decision_value = output.get("decision")
            if decision_value:
                decision = DecisionOutcome(decision_value)
            if final_entry.decision_artifact is not None:
                decision = final_entry.decision_artifact.verdict
            epistemic = final_entry.epistemic_verdict or EpistemicVerdict.CERTAIN
            confidence = float(output.get("confidence", 0.0))
            stop_reason = final_entry.stop_reason

        model_metadata = trace.header.model_metadata
        if model_metadata is None:
            raise RuntimeError("Trace header missing model metadata")

        return cls(
            status=status,
            decision=decision,
            epistemic_verdict=epistemic,
            confidence=confidence,
            stop_reason=stop_reason,
            model_metadata=model_metadata,
        )


__all__ = ["PipelineStatus", "PipelineResult"]
