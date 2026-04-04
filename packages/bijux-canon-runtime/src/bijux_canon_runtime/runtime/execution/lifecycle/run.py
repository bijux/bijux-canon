# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution run helpers for `LiveExecutor`."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
import os
import signal

from bijux_canon_runtime.core.errors import NonDeterminismViolationError
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.observability.capture.time import utc_now_deterministic
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.ontology.ids import (
    ClaimID,
    ContentHash,
    ToolID,
)
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.runtime.execution.agent_executor import AgentExecutor
from bijux_canon_runtime.runtime.execution.event_causality import event_causality_tag
from bijux_canon_runtime.runtime.execution.lifecycle.step_operations import (
    StepCallbacks,
    StepServices,
    execute_agent_step,
    execute_reasoning_step,
    execute_retrieval_step,
    record_flow_verification,
    verify_step_outcome,
)
from bijux_canon_runtime.runtime.execution.reasoning_executor import ReasoningExecutor
from bijux_canon_runtime.runtime.execution.retrieval_executor import RetrievalExecutor
from bijux_canon_runtime.verification.orchestrator import VerificationOrchestrator


def run_execution(
    *,
    steps_plan,
    context: ExecutionContext,
    state_cls,
    handle_verification_override: Callable,
):
    """Internal helper; not part of the public API."""
    recorder = context.trace_recorder
    event_index = context.starting_event_index
    artifacts: list[Artifact] = list(context.initial_artifacts)
    evidence: list[RetrievedEvidence] = list(context.initial_evidence)
    reasoning_bundles: list[ReasoningBundle] = []
    verification_results: list[VerificationResult] = []
    verification_arbitrations: list[VerificationArbitration] = []
    tool_invocations: list[ToolInvocation] = list(context.initial_tool_invocations)
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

    evidence_index = context.starting_evidence_index
    tool_invocation_index = context.starting_tool_invocation_index
    entropy_index = context.starting_entropy_index
    entropy_checked_index = context.starting_entropy_index

    def record_event(
        event_type: EventType, step_index: int, payload: dict[str, object]
    ) -> None:
        """Execute record_event and enforce its contract."""
        nonlocal event_index
        payload["event_type"] = event_type.value
        event = ExecutionEvent(
            spec_version="v1",
            event_index=event_index,
            step_index=step_index,
            event_type=event_type,
            causality_tag=event_causality_tag(event_type),
            timestamp_utc=utc_now_deterministic(event_index),
            payload=payload,
            payload_hash=fingerprint_inputs(payload),
        )
        recorder.record(
            event,
            context.authority,
        )
        if context.execution_store is not None and context.run_id is not None:
            context.execution_store.save_events(
                run_id=context.run_id,
                tenant_id=context.tenant_id,
                events=(event,),
            )
        for observer in context.observers:
            observer.on_event(event)
        with suppress(Exception):
            context.consume_budget(trace_events=1)
        event_index += 1

    def record_tool_invocation(invocation: ToolInvocation) -> None:
        """Execute record_tool_invocation and enforce its contract."""
        nonlocal tool_invocation_index
        tool_invocations.append(invocation)
        if context.execution_store is not None and context.run_id is not None:
            context.execution_store.append_tool_invocations(
                run_id=context.run_id,
                tenant_id=context.tenant_id,
                tool_invocations=(invocation,),
                starting_index=tool_invocation_index,
            )
        tool_invocation_index += 1

    def record_evidence(items: list[RetrievedEvidence]) -> None:
        """Execute record_evidence and enforce its contract."""
        nonlocal evidence_index
        if not items:
            return
        if context.execution_store is not None and context.run_id is not None:
            context.execution_store.append_evidence(
                run_id=context.run_id,
                evidence=items,
                starting_index=evidence_index,
            )
        evidence_index += len(items)

    def record_artifacts(items: list[Artifact]) -> None:
        """Execute record_artifacts and enforce its contract."""
        if not items:
            return
        if context.execution_store is not None and context.run_id is not None:
            context.execution_store.save_artifacts(
                run_id=context.run_id, artifacts=items
            )

    def record_claims(claims: tuple[ClaimID, ...]) -> None:
        """Execute record_claims and enforce its contract."""
        if not claims:
            return
        if context.execution_store is not None and context.run_id is not None:
            context.execution_store.append_claim_ids(
                run_id=context.run_id,
                tenant_id=context.tenant_id,
                claim_ids=claims,
            )

    def flush_entropy_usage() -> None:
        """Execute flush_entropy_usage and enforce its contract."""
        nonlocal entropy_index
        if context.execution_store is None or context.run_id is None:
            return
        usage = context.entropy_usage()
        if len(usage) <= entropy_index:
            return
        new_entries = usage[entropy_index:]
        context.execution_store.append_entropy_usage(
            run_id=context.run_id,
            usage=new_entries,
            starting_index=entropy_index,
        )
        entropy_index = len(usage)

    def enforce_entropy_authorization() -> None:
        """Execute enforce_entropy_authorization and enforce its contract."""
        nonlocal entropy_checked_index
        usage = context.entropy_usage()
        if len(usage) <= entropy_checked_index:
            return
        new_entries = usage[entropy_checked_index:]
        entropy_checked_index = len(usage)
        if not context.strict_determinism:
            return
        for entry in new_entries:
            if not entry.nondeterminism_source.authorized:
                raise NonDeterminismViolationError(
                    "entropy source used without explicit authorization"
                )

    def save_checkpoint(step_index: int) -> None:
        """Execute save_checkpoint and enforce its contract."""
        if context.execution_store is None or context.run_id is None:
            return
        context.execution_store.save_checkpoint(
            run_id=context.run_id,
            tenant_id=context.tenant_id,
            step_index=step_index,
            event_index=event_index - 1,
        )

    previous_handler = signal.getsignal(signal.SIGINT)

    def _handle_interrupt(_signum, _frame) -> None:
        """Internal helper; not part of the public API."""
        context.cancel()

    signal.signal(signal.SIGINT, _handle_interrupt)
    try:
        interrupted = execute_steps(
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
            handle_verification_override=handle_verification_override,
        )
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    return state_cls(
        recorder=recorder,
        event_index=event_index,
        artifacts=artifacts,
        evidence=evidence,
        reasoning_bundles=reasoning_bundles,
        verification_results=verification_results,
        verification_arbitrations=verification_arbitrations,
        tool_invocations=tool_invocations,
        pending_invocations=pending_invocations,
        interrupted=interrupted,
    )


def execute_steps(
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
    handle_verification_override: Callable,
) -> bool:
    """Internal helper; not part of the public API."""
    interrupted = False
    # Step-by-step execution loop.
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

        # Forced verification override.
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

    # Phase exit: flow-level verification.
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


__all__ = ["run_execution", "execute_steps"]
