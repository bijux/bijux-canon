# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Step-loop helpers for execution lifecycles."""

from __future__ import annotations

from collections.abc import Callable
import os
import signal

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.ontology.ids import (
    ClaimID,
    ContentHash,
    ToolID,
)
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.runtime.execution.agent_executor import AgentExecutor
from bijux_canon_runtime.runtime.execution.lifecycle.step_operations import (
    StepCallbacks,
    StepServices,
    VerificationOverrideHandler,
    execute_agent_step,
    execute_reasoning_step,
    execute_retrieval_step,
    record_flow_verification,
    verify_step_outcome,
)
from bijux_canon_runtime.runtime.execution.reasoning_executor import ReasoningExecutor
from bijux_canon_runtime.runtime.execution.retrieval_executor import RetrievalExecutor
from bijux_canon_runtime.verification.orchestrator import VerificationOrchestrator


def execute_steps(
    *,
    steps_plan: ExecutionSteps,
    context: ExecutionContext,
    record_event: Callable[[EventType, int, dict[str, object]], None],
    record_tool_invocation: Callable[[ToolInvocation], None],
    record_evidence: Callable[[list[RetrievedEvidence]], None],
    record_artifacts: Callable[[list[Artifact]], None],
    record_claims: Callable[[tuple[ClaimID, ...]], None],
    flush_entropy_usage: Callable[[], None],
    enforce_entropy_authorization: Callable[[], None],
    save_checkpoint: Callable[[int], None],
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
    handle_verification_override: VerificationOverrideHandler,
) -> bool:
    """Execute the step-by-step runtime loop."""
    interrupted = False
    callbacks = StepCallbacks(
        record_event=record_event,
        record_tool_invocation=record_tool_invocation,
        record_evidence=record_evidence,
        record_artifacts=record_artifacts,
        record_claims=record_claims,
        flush_entropy_usage=flush_entropy_usage,
        enforce_entropy_authorization=enforce_entropy_authorization,
        save_checkpoint=save_checkpoint,
    )
    services = StepServices(
        agent_executor=agent_executor,
        retrieval_executor=retrieval_executor,
        reasoning_executor=reasoning_executor,
        verification_orchestrator=verification_orchestrator,
        policy=policy,
        tool_agent=tool_agent,
        tool_retrieval=tool_retrieval,
        tool_reasoning=tool_reasoning,
        handle_verification_override=handle_verification_override,
    )
    for step in steps_plan.steps:
        if step.step_index <= context.resume_from_step_index:
            continue
        if context.is_cancelled():
            record_event(
                EventType.EXECUTION_INTERRUPTED,
                step.step_index,
                {"step_index": step.step_index, "reason": "sigint"},
            )
            interrupted = True
            break
        current_evidence: list[RetrievedEvidence] = []
        context.record_evidence(step.step_index, [])
        context.start_step_budget()
        record_event(
            EventType.STEP_START,
            step.step_index,
            {
                "step_index": step.step_index,
                "agent_id": step.agent_id,
            },
        )
        try:
            context.consume_budget(steps=1)
        except Exception as exc:
            record_event(
                EventType.STEP_FAILED,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "agent_id": step.agent_id,
                    "error": str(exc),
                },
            )
            break

        should_stop, current_evidence = execute_retrieval_step(
            step=step,
            context=context,
            callbacks=callbacks,
            services=services,
            evidence=evidence,
            pending_invocations=pending_invocations,
        )
        if should_stop:
            break

        should_stop, step_artifacts = execute_agent_step(
            step=step,
            context=context,
            callbacks=callbacks,
            services=services,
            artifacts=artifacts,
            current_evidence=current_evidence,
            pending_invocations=pending_invocations,
        )
        if should_stop:
            break

        forced_action = handle_verification_override(
            step=step,
            context=context,
            record_event=record_event,
            verification_results=verification_results,
            step_artifacts=step_artifacts,
        )
        if forced_action == "continue":
            continue
        if forced_action == "break":
            break

        should_stop, bundle = execute_reasoning_step(
            step=step,
            context=context,
            callbacks=callbacks,
            services=services,
            artifacts=artifacts,
            current_evidence=current_evidence,
            step_artifacts=step_artifacts,
            pending_invocations=pending_invocations,
            reasoning_bundles=reasoning_bundles,
        )
        if should_stop or bundle is None:
            break

        should_stop = verify_step_outcome(
            step=step,
            context=context,
            callbacks=callbacks,
            services=services,
            current_evidence=current_evidence,
            step_artifacts=step_artifacts,
            bundle=bundle,
            verification_results=verification_results,
            verification_arbitrations=verification_arbitrations,
        )
        if should_stop:
            break
        crash_step = os.environ.get("AF_CRASH_AT_STEP")
        if crash_step is not None and int(crash_step) == step.step_index:
            os.kill(os.getpid(), signal.SIGKILL)

    if not interrupted:
        record_flow_verification(
            steps_plan=steps_plan,
            callbacks=callbacks,
            services=services,
            reasoning_bundles=reasoning_bundles,
            verification_results=verification_results,
            verification_arbitrations=verification_arbitrations,
        )
    return interrupted


__all__ = ["execute_steps"]
