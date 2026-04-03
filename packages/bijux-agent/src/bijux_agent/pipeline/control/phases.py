"""Defines the canonical pipeline lifecycle and phase metadata."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from bijux_agent.enums import AgentType

from .stop_conditions import StopReason


class PipelinePhase(str, Enum):
    """Each phase follows the single canonical lifecycle declared here."""

    INIT = "INIT"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    JUDGE = "JUDGE"
    VERIFY = "VERIFY"
    FINALIZE = "FINALIZE"
    DONE = "DONE"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class PhaseInfo:
    entry_conditions: Sequence[str]
    exit_conditions: Sequence[str]
    allowed_agents: Sequence[AgentType]
    stop_reasons: Sequence[StopReason]


PHASE_SEQUENCE: tuple[PipelinePhase, ...] = (
    PipelinePhase.INIT,
    PipelinePhase.PLAN,
    PipelinePhase.EXECUTE,
    PipelinePhase.JUDGE,
    PipelinePhase.VERIFY,
    PipelinePhase.FINALIZE,
    PipelinePhase.DONE,
)

PIPELINE_PHASE_ORDER: list[PipelinePhase] = [
    PipelinePhase.INIT,
    PipelinePhase.PLAN,
    PipelinePhase.EXECUTE,
    PipelinePhase.JUDGE,
    PipelinePhase.VERIFY,
    PipelinePhase.FINALIZE,
    PipelinePhase.DONE,
]

PHASE_DETAILS: dict[PipelinePhase, PhaseInfo] = {
    PipelinePhase.INIT: PhaseInfo(
        entry_conditions=("context_ready",),
        exit_conditions=("plan_started",),
        allowed_agents=(),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.FATAL_FAILURE),
    ),
    PipelinePhase.PLAN: PhaseInfo(
        entry_conditions=("plan_requested",),
        exit_conditions=("plan_completed",),
        allowed_agents=(AgentType.PLANNER,),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.MAX_ITERATIONS),
    ),
    PipelinePhase.EXECUTE: PhaseInfo(
        entry_conditions=("retrieval_done",),
        exit_conditions=("execution_finished",),
        allowed_agents=(
            AgentType.READER,
            AgentType.SUMMARIZER,
            AgentType.TASKHANDLER,
            AgentType.CRITIQUE,
        ),
        stop_reasons=(
            StopReason.USER_INTERRUPTION,
            StopReason.BUDGET_EXCEEDED,
            StopReason.CONFIDENCE_THRESHOLD_MET,
        ),
    ),
    PipelinePhase.JUDGE: PhaseInfo(
        entry_conditions=("execution_traces_available",),
        exit_conditions=("judgment_recorded",),
        allowed_agents=(AgentType.JUDGE,),
        stop_reasons=(
            StopReason.USER_INTERRUPTION,
            StopReason.VERIFICATION_VETO,
            StopReason.MAX_ITERATIONS,
        ),
    ),
    PipelinePhase.VERIFY: PhaseInfo(
        entry_conditions=("judgment_finalized",),
        exit_conditions=("verification_completed",),
        allowed_agents=(AgentType.VERIFIER,),
        stop_reasons=(
            StopReason.VERIFICATION_VETO,
            StopReason.USER_INTERRUPTION,
            StopReason.FATAL_FAILURE,
        ),
    ),
    PipelinePhase.FINALIZE: PhaseInfo(
        entry_conditions=("verification_passed",),
        exit_conditions=("final_record_saved",),
        allowed_agents=(AgentType.ORCHESTRATOR,),
        stop_reasons=(
            StopReason.CONFIDENCE_THRESHOLD_MET,
            StopReason.MAX_ITERATIONS,
            StopReason.USER_INTERRUPTION,
        ),
    ),
    PipelinePhase.DONE: PhaseInfo(
        entry_conditions=("finalized",),
        exit_conditions=(),
        allowed_agents=(),
        stop_reasons=(),
    ),
    PipelinePhase.ABORTED: PhaseInfo(
        entry_conditions=("abort_triggered",),
        exit_conditions=("cleanup_completed",),
        allowed_agents=(),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.FATAL_FAILURE),
    ),
}
