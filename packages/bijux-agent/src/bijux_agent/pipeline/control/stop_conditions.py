"""Machine-readable stop reasons used throughout the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StopReason(str, Enum):
    USER_INTERRUPTION = "user_interruption"
    CONVERGENCE_REACHED = "convergence_reached"
    CONFIDENCE_THRESHOLD_MET = "confidence_threshold_met"
    BUDGET_EXCEEDED = "budget_exceeded"
    MAX_ITERATIONS = "max_iterations"
    VERIFICATION_VETO = "verification_veto"
    FATAL_FAILURE = "fatal_failure"
    EPISTEMIC_FAILURE = "epistemic_failure"


@dataclass(frozen=True)
class StopCondition:
    reason: StopReason
    description: str


STOP_CONDITIONS: tuple[StopCondition, ...] = (
    StopCondition(
        reason=StopReason.USER_INTERRUPTION,
        description="User requested cancellation (SIGINT or manual flag).",
    ),
    StopCondition(
        reason=StopReason.CONVERGENCE_REACHED,
        description="Run reached stability across scores, verdicts, and confidence.",
    ),
    StopCondition(
        reason=StopReason.CONFIDENCE_THRESHOLD_MET,
        description="Confidence exceeded the configured threshold for success.",
    ),
    StopCondition(
        reason=StopReason.BUDGET_EXCEEDED,
        description="Cost/budget limit reached before finalization.",
    ),
    StopCondition(
        reason=StopReason.MAX_ITERATIONS,
        description="Maximum iteration count for feedback loops reached.",
    ),
    StopCondition(
        reason=StopReason.VERIFICATION_VETO,
        description="Verifier agent issued a veto, halting the run.",
    ),
    StopCondition(
        reason=StopReason.FATAL_FAILURE,
        description="Unhandled fatal failure in the execution graph.",
    ),
    StopCondition(
        reason=StopReason.EPISTEMIC_FAILURE,
        description="Knowledge boundary prevents a confident decision.",
    ),
)
