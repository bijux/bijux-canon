# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution run helpers for `LiveExecutor`."""

from __future__ import annotations

from collections.abc import Callable
import signal
from types import FrameType
from typing import TypeVar

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.ontology.ids import (
    ContentHash,
    ToolID,
)
from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.runtime.execution.agent_executor import AgentExecutor
from bijux_canon_runtime.runtime.execution.lifecycle.run_recording import (
    ExecutionRunRecorder,
)
from bijux_canon_runtime.runtime.execution.lifecycle.step_loop import execute_steps
from bijux_canon_runtime.runtime.execution.lifecycle.step_operations import (
    VerificationOverrideHandler,
)
from bijux_canon_runtime.runtime.execution.reasoning_executor import ReasoningExecutor
from bijux_canon_runtime.runtime.execution.retrieval_executor import RetrievalExecutor
from bijux_canon_runtime.verification.orchestrator import VerificationOrchestrator

StateT = TypeVar("StateT")


def run_execution(
    *,
    steps_plan: ExecutionSteps,
    context: ExecutionContext,
    state_cls: Callable[..., StateT],
    handle_verification_override: VerificationOverrideHandler,
) -> StateT:
    """Internal helper; not part of the public API."""
    recorder = context.trace_recorder
    artifacts: list[Artifact] = list(context.initial_artifacts)
    evidence: list[RetrievedEvidence] = list(context.initial_evidence)
    reasoning_bundles: list[ReasoningBundle] = []
    verification_results: list[VerificationResult] = []
    verification_arbitrations: list[VerificationArbitration] = []
    tool_invocations: list[ToolInvocation] = list(context.initial_tool_invocations)
    run_recorder = ExecutionRunRecorder.from_context(
        context=context,
        recorder=recorder,
        tool_invocations=tool_invocations,
    )
    agent_executor = AgentExecutor()
    retrieval_executor = RetrievalExecutor()
    reasoning_executor = ReasoningExecutor()
    verification_orchestrator = VerificationOrchestrator()
    policy = context.verification_policy
    tool_agent = ToolID("bijux-agent.run")
    tool_retrieval = ToolID("bijux-rag.retrieve")
    tool_reasoning = ToolID("bijux-rar.reason")
    pending_invocations: dict[tuple[int, ToolID], ContentHash] = {}
    interrupted = False

    previous_handler = signal.getsignal(signal.SIGINT)

    def _handle_interrupt(_signum: int, _frame: FrameType | None) -> None:
        """Internal helper; not part of the public API."""
        context.cancel()

    signal.signal(signal.SIGINT, _handle_interrupt)
    try:
        interrupted = execute_steps(
            steps_plan=steps_plan,
            context=context,
            record_event=run_recorder.record_event,
            record_tool_invocation=run_recorder.record_tool_invocation,
            record_evidence=run_recorder.record_evidence,
            record_artifacts=run_recorder.record_artifacts,
            record_claims=run_recorder.record_claims,
            flush_entropy_usage=run_recorder.flush_entropy_usage,
            enforce_entropy_authorization=run_recorder.enforce_entropy_authorization,
            save_checkpoint=run_recorder.save_checkpoint,
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
            handle_verification_override=handle_verification_override,
        )
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    return state_cls(
        recorder=recorder,
        event_index=run_recorder.event_index,
        artifacts=artifacts,
        evidence=evidence,
        reasoning_bundles=reasoning_bundles,
        verification_results=verification_results,
        verification_arbitrations=verification_arbitrations,
        tool_invocations=tool_invocations,
        pending_invocations=pending_invocations,
        interrupted=interrupted,
    )


__all__ = ["run_execution"]
