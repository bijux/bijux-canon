# INTERNAL — SUBJECT TO CHANGE WITHOUT NOTICE
# INTERNAL API — NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/execution/live_executor.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from agentic_flows.runtime.context import ExecutionContext, RunMode
from agentic_flows.runtime.execution.phases import (
    execute_step_phase,
    execution_phase,
    finalization_phase,
    planning_phase,
)
from agentic_flows.runtime.execution.step_executor import ExecutionOutcome
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from agentic_flows.spec.model.verification.verification_result import VerificationResult
from agentic_flows.spec.ontology import (
    CausalityTag,
    VerificationPhase,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import ContentHash, RuleID, ToolID
from agentic_flows.spec.ontology.public import EventType

if TYPE_CHECKING:
    from agentic_flows.runtime.execution.agent_executor import AgentExecutor
    from agentic_flows.runtime.execution.reasoning_executor import ReasoningExecutor
    from agentic_flows.runtime.execution.retrieval_executor import RetrievalExecutor
    from agentic_flows.runtime.verification_engine import VerificationOrchestrator


@dataclass
class _PhaseState:
    """Internal helper type; not part of the public API."""

    recorder: object
    event_index: int
    artifacts: list[Artifact]
    evidence: list[RetrievedEvidence]
    reasoning_bundles: list[ReasoningBundle]
    verification_results: list[VerificationResult]
    verification_arbitrations: list[VerificationArbitration]
    tool_invocations: list[ToolInvocation]
    pending_invocations: dict[tuple[int, ToolID], ContentHash]
    interrupted: bool


def _notify_stage(context: ExecutionContext, stage: str, phase: str) -> None:
    """Internal helper; not part of the public API."""
    hook_name = f"on_stage_{phase}"
    for observer in context.observers:
        hook = getattr(observer, hook_name, None)
        if callable(hook):
            hook(stage)


_EVENT_CAUSALITY = {
    EventType.TOOL_CALL_START: CausalityTag.TOOL,
    EventType.TOOL_CALL_END: CausalityTag.TOOL,
    EventType.TOOL_CALL_FAIL: CausalityTag.TOOL,
    EventType.RETRIEVAL_START: CausalityTag.DATASET,
    EventType.RETRIEVAL_END: CausalityTag.DATASET,
    EventType.RETRIEVAL_FAILED: CausalityTag.DATASET,
    EventType.HUMAN_INTERVENTION: CausalityTag.HUMAN,
    EventType.EXECUTION_INTERRUPTED: CausalityTag.ENVIRONMENT,
    EventType.SEMANTIC_VIOLATION: CausalityTag.ENVIRONMENT,
}


def _causality_tag(event_type: EventType) -> CausalityTag:
    """Internal helper; not part of the public API."""
    return _EVENT_CAUSALITY.get(event_type, CausalityTag.AGENT)


class LiveExecutor:
    """Behavioral contract for LiveExecutor."""

    def execute(
        self,
        plan: ExecutionPlan,
        context: ExecutionContext,
    ) -> ExecutionOutcome:
        """Execute execute and enforce its contract."""
        _notify_stage(context, "planning", "start")
        steps_plan = self._planning_phase(plan)
        _notify_stage(context, "planning", "end")
        _notify_stage(context, "execution", "start")
        phase_state = self._execution_phase(steps_plan, context)
        _notify_stage(context, "execution", "end")
        _notify_stage(context, "finalization", "start")
        result = self._finalization_phase(steps_plan, context, phase_state)
        _notify_stage(context, "finalization", "end")
        return result

    @staticmethod
    def _planning_phase(plan: ExecutionPlan):
        """Internal helper; not part of the public API."""
        return planning_phase(plan)

    def _execution_phase(self, steps_plan, context: ExecutionContext) -> _PhaseState:
        """Internal helper; not part of the public API."""
        return execution_phase(
            steps_plan=steps_plan,
            context=context,
            phase_state_cls=_PhaseState,
            handle_verification_phase_override=self._handle_verification_phase_override,
        )

    def _execute_step_phase(
        self,
        *,
        steps_plan,
        context: ExecutionContext,
        record_event,
        record_tool_invocation,
        record_evidence,
        record_artifacts,
        record_claims,
        flush_entropy_usage,
        enforce_entropy_authorization,
        save_checkpoint,
        artifacts: list[Artifact],
        evidence: list[RetrievedEvidence],
        reasoning_bundles: list[ReasoningBundle],
        verification_results: list[VerificationResult],
        verification_arbitrations: list[VerificationArbitration],
        tool_invocations: list[ToolInvocation],
        pending_invocations: dict[tuple[int, ToolID], ContentHash],
        agent_executor: AgentExecutor,
        retrieval_executor: RetrievalExecutor,
        reasoning_executor: ReasoningExecutor,
        verification_orchestrator: VerificationOrchestrator,
        policy: VerificationPolicy | None,
        tool_agent: ToolID,
        tool_retrieval: ToolID,
        tool_reasoning: ToolID,
    ) -> bool:
        """Internal helper; not part of the public API."""
        return execute_step_phase(
            steps_plan=steps_plan,
            context=context,
            record_event=record_event,
            record_tool_invocation=record_tool_invocation,
            record_evidence=record_evidence,
            record_artifacts=record_artifacts,
            record_claims=record_claims,
            flush_entropy_usage=flush_entropy_usage,
            enforce_entropy_authorization=enforce_entropy_authorization,
            save_checkpoint=save_checkpoint,
            artifacts=artifacts,
            evidence=evidence,
            reasoning_bundles=reasoning_bundles,
            verification_results=verification_results,
            verification_arbitrations=verification_arbitrations,
            tool_invocations=tool_invocations,
            pending_invocations=pending_invocations,
            agent_executor=agent_executor,
            retrieval_executor=retrieval_executor,
            reasoning_executor=reasoning_executor,
            verification_orchestrator=verification_orchestrator,
            policy=policy,
            tool_agent=tool_agent,
            tool_retrieval=tool_retrieval,
            tool_reasoning=tool_reasoning,
            handle_verification_phase_override=self._handle_verification_phase_override,
        )

    def _handle_verification_phase_override(
        self,
        *,
        step,
        context: ExecutionContext,
        record_event,
        verification_results: list[VerificationResult],
        step_artifacts: list[Artifact],
    ) -> str | None:
        """Internal helper; not part of the public API."""
        if str(step.agent_id) != "force-partial-failure":
            return None
        verification_results.append(
            VerificationResult(
                spec_version="v1",
                engine_id="forced",
                status="FAIL",
                reason="forced_partial_failure",
                randomness=VerificationRandomness.DETERMINISTIC,
                violations=(RuleID("forced_partial_failure"),),
                checked_artifact_ids=tuple(
                    artifact.artifact_id for artifact in step_artifacts
                ),
                phase=VerificationPhase.POST_EXECUTION,
                rules_applied=(),
                decision="FAIL",
            )
        )
        record_event(
            EventType.VERIFICATION_FAIL,
            step.step_index,
            {
                "step_index": step.step_index,
                "status": "FAIL",
                "rule_ids": ["forced_partial_failure"],
            },
        )
        record_event(
            EventType.STEP_FAILED,
            step.step_index,
            {
                "step_index": step.step_index,
                "agent_id": step.agent_id,
                "error": "forced_partial_failure",
            },
        )
        if context.mode == RunMode.UNSAFE:
            record_event(
                EventType.SEMANTIC_VIOLATION,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "decision": "FAIL",
                    "rule_ids": ["forced_partial_failure"],
                },
            )
            return "continue"
        return "break"

    def _finalization_phase(
        self,
        steps_plan,
        context: ExecutionContext,
        state: _PhaseState,
    ) -> ExecutionOutcome:
        """Internal helper; not part of the public API."""
        return finalization_phase(
            steps_plan=steps_plan,
            context=context,
            state=state,
            resolver_id_from_metadata=self._resolver_id_from_metadata,
        )

    @staticmethod
    def _resolver_id_from_metadata(metadata: tuple[tuple[str, str], ...]) -> str:
        """Internal helper; not part of the public API."""
        for key, value in metadata:
            if key == "resolver_id":
                return value
        raise ValueError("resolution_metadata missing resolver_id")
