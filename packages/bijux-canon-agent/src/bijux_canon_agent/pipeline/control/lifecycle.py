"""Defines the canonical pipeline lifecycle and lifecycle metadata."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_agent.enums import AgentType

from .stop_conditions import StopReason


class PipelineLifecycle(StrEnum):
    """Each lifecycle step follows the canonical flow declared here."""

    INIT = "INIT"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    JUDGE = "JUDGE"
    VERIFY = "VERIFY"
    FINALIZE = "FINALIZE"
    DONE = "DONE"
    ABORTED = "ABORTED"


@dataclass(frozen=True)
class LifecycleInfo:
    entry_conditions: Sequence[str]
    exit_conditions: Sequence[str]
    allowed_agents: Sequence[AgentType]
    stop_reasons: Sequence[StopReason]


PIPELINE_LIFECYCLE: tuple[PipelineLifecycle, ...] = (
    PipelineLifecycle.INIT,
    PipelineLifecycle.PLAN,
    PipelineLifecycle.EXECUTE,
    PipelineLifecycle.JUDGE,
    PipelineLifecycle.VERIFY,
    PipelineLifecycle.FINALIZE,
    PipelineLifecycle.DONE,
)

PIPELINE_LIFECYCLE_ORDER: list[PipelineLifecycle] = [
    PipelineLifecycle.INIT,
    PipelineLifecycle.PLAN,
    PipelineLifecycle.EXECUTE,
    PipelineLifecycle.JUDGE,
    PipelineLifecycle.VERIFY,
    PipelineLifecycle.FINALIZE,
    PipelineLifecycle.DONE,
]

LIFECYCLE_DETAILS: dict[PipelineLifecycle, LifecycleInfo] = {
    PipelineLifecycle.INIT: LifecycleInfo(
        entry_conditions=("context_ready",),
        exit_conditions=("plan_started",),
        allowed_agents=(),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.FATAL_FAILURE),
    ),
    PipelineLifecycle.PLAN: LifecycleInfo(
        entry_conditions=("plan_requested",),
        exit_conditions=("plan_completed",),
        allowed_agents=(AgentType.PLANNER,),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.MAX_ITERATIONS),
    ),
    PipelineLifecycle.EXECUTE: LifecycleInfo(
        entry_conditions=("retrieval_done",),
        exit_conditions=("execution_finished",),
        allowed_agents=(
            AgentType.READER,
            AgentType.SUMMARIZER,
            AgentType.STAGE_RUNNER,
            AgentType.CRITIQUE,
        ),
        stop_reasons=(
            StopReason.USER_INTERRUPTION,
            StopReason.BUDGET_EXCEEDED,
            StopReason.CONFIDENCE_THRESHOLD_MET,
        ),
    ),
    PipelineLifecycle.JUDGE: LifecycleInfo(
        entry_conditions=("execution_traces_available",),
        exit_conditions=("judgment_recorded",),
        allowed_agents=(AgentType.JUDGE,),
        stop_reasons=(
            StopReason.USER_INTERRUPTION,
            StopReason.VERIFICATION_VETO,
            StopReason.MAX_ITERATIONS,
        ),
    ),
    PipelineLifecycle.VERIFY: LifecycleInfo(
        entry_conditions=("judgment_finalized",),
        exit_conditions=("verification_completed",),
        allowed_agents=(AgentType.VERIFIER,),
        stop_reasons=(
            StopReason.VERIFICATION_VETO,
            StopReason.USER_INTERRUPTION,
            StopReason.FATAL_FAILURE,
        ),
    ),
    PipelineLifecycle.FINALIZE: LifecycleInfo(
        entry_conditions=("verification_passed",),
        exit_conditions=("final_record_saved",),
        allowed_agents=(AgentType.ORCHESTRATOR,),
        stop_reasons=(
            StopReason.CONFIDENCE_THRESHOLD_MET,
            StopReason.MAX_ITERATIONS,
            StopReason.USER_INTERRUPTION,
        ),
    ),
    PipelineLifecycle.DONE: LifecycleInfo(
        entry_conditions=("finalized",),
        exit_conditions=(),
        allowed_agents=(),
        stop_reasons=(),
    ),
    PipelineLifecycle.ABORTED: LifecycleInfo(
        entry_conditions=("abort_triggered",),
        exit_conditions=("cleanup_completed",),
        allowed_agents=(),
        stop_reasons=(StopReason.USER_INTERRUPTION, StopReason.FATAL_FAILURE),
    ),
}
