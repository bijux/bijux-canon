# INTERNAL — SUBJECT TO CHANGE WITHOUT NOTICE
# INTERNAL API — NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for runtime/execution/live_executor.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bijux_canon_runtime.runtime.context import ExecutionContext, RunMode
from bijux_canon_runtime.runtime.execution.lifecycle import (
    execute_steps,
    finalize_execution,
    prepare_execution,
    run_execution,
)
from bijux_canon_runtime.runtime.execution.step_executor import ExecutionOutcome
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import VerificationResult
from bijux_canon_runtime.ontology import (
    CausalityTag,
    VerificationPhase,
    VerificationRandomness,
)
from bijux_canon_runtime.ontology.ids import ContentHash, RuleID, ToolID
from bijux_canon_runtime.ontology.public import EventType

if TYPE_CHECKING:
    from bijux_canon_runtime.runtime.execution.agent_executor import AgentExecutor
    from bijux_canon_runtime.runtime.execution.reasoning_executor import ReasoningExecutor
    from bijux_canon_runtime.runtime.execution.retrieval_executor import RetrievalExecutor
    from bijux_canon_runtime.verification.orchestrator import VerificationOrchestrator


@dataclass
class _ExecutionState:
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
        steps_plan = self._prepare_execution(plan)
        _notify_stage(context, "planning", "end")
        _notify_stage(context, "execution", "start")
        execution_state = self._run_execution(steps_plan, context)
        _notify_stage(context, "execution", "end")
        _notify_stage(context, "finalization", "start")
        result = self._finalize_execution(steps_plan, context, execution_state)
        _notify_stage(context, "finalization", "end")
        return result

    @staticmethod
    def _prepare_execution(plan: ExecutionPlan):
        """Internal helper; not part of the public API."""
        return prepare_execution(plan)

    def _run_execution(self, steps_plan, context: ExecutionContext) -> _ExecutionState:
        """Internal helper; not part of the public API."""
        return run_execution(
            steps_plan=steps_plan,
            context=context,
            state_cls=_ExecutionState,
            handle_verification_override=self._handle_verification_override,
        )

    def _execute_steps(
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
        return execute_steps(
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
            handle_verification_override=self._handle_verification_override,
        )

    def _handle_verification_override(
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

    def _finalize_execution(
        self,
        steps_plan,
        context: ExecutionContext,
        state: _ExecutionState,
    ) -> ExecutionOutcome:
        """Internal helper; not part of the public API."""
        return finalize_execution(
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
