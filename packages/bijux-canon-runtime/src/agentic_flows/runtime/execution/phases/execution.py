# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Execution phase helpers for LiveExecutor."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
import os
import signal

from agentic_flows.core.errors import NonDeterminismViolationError
from agentic_flows.runtime.context import ExecutionContext, RunMode
from agentic_flows.runtime.execution.agent_executor import AgentExecutor
from agentic_flows.runtime.execution.reasoning_executor import ReasoningExecutor
from agentic_flows.runtime.execution.retrieval_executor import RetrievalExecutor
from agentic_flows.runtime.observability.capture.time import utc_now_deterministic
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from agentic_flows.runtime.observability.classification.retrieval_fingerprint import (
    fingerprint_retrieval,
)
from agentic_flows.runtime.verification_engine import VerificationOrchestrator
from agentic_flows.spec.contracts.step_contract import validate_outputs
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from agentic_flows.spec.model.verification.verification_result import VerificationResult
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
    CausalityTag,
    StepType,
    VerificationPhase,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import (
    ArtifactID,
    ClaimID,
    ContentHash,
    RuleID,
    ToolID,
)
from agentic_flows.spec.ontology.public import EventType


def execution_phase(
    *,
    steps_plan,
    context: ExecutionContext,
    phase_state_cls,
    handle_verification_phase_override: Callable,
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
            causality_tag=_causality_tag(event_type),
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
        interrupted = execute_step_phase(
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
            handle_verification_phase_override=handle_verification_phase_override,
        )
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    return phase_state_cls(
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


def execute_step_phase(
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
    handle_verification_phase_override: Callable,
) -> bool:
    """Internal helper; not part of the public API."""
    interrupted = False
    # Phase entry: per-step execution.
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

        # Phase: retrieval (optional).
        if step.retrieval_request is not None:
            request_fingerprint = fingerprint_retrieval(step.retrieval_request)
            record_event(
                EventType.RETRIEVAL_START,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "request_id": step.retrieval_request.request_id,
                    "vector_contract_id": step.retrieval_request.vector_contract_id,
                    "request_fingerprint": request_fingerprint,
                },
            )
            tool_input = {
                "tool_id": tool_retrieval,
                "request_id": step.retrieval_request.request_id,
                "vector_contract_id": step.retrieval_request.vector_contract_id,
                "request_fingerprint": request_fingerprint,
            }
            record_event(
                EventType.TOOL_CALL_START,
                step.step_index,
                {
                    "tool_id": tool_retrieval,
                    "input_fingerprint": fingerprint_inputs(tool_input),
                },
            )
            pending_invocations[(step.step_index, tool_retrieval)] = ContentHash(
                fingerprint_inputs(tool_input)
            )

            try:
                retrieved = retrieval_executor.execute(step, context)
            except Exception as exc:
                input_fingerprint = pending_invocations.pop(
                    (step.step_index, tool_retrieval),
                    ContentHash(fingerprint_inputs(tool_input)),
                )
                record_tool_invocation(
                    ToolInvocation(
                        spec_version="v1",
                        tool_id=tool_retrieval,
                        determinism_level=step.determinism_level,
                        inputs_fingerprint=input_fingerprint,
                        outputs_fingerprint=None,
                        duration=0.0,
                        outcome="fail",
                    )
                )
                record_event(
                    EventType.TOOL_CALL_FAIL,
                    step.step_index,
                    {
                        "tool_id": tool_retrieval,
                        "input_fingerprint": fingerprint_inputs(tool_input),
                        "error": str(exc),
                    },
                )
                record_event(
                    EventType.RETRIEVAL_FAILED,
                    step.step_index,
                    {
                        "step_index": step.step_index,
                        "request_id": step.retrieval_request.request_id,
                        "vector_contract_id": step.retrieval_request.vector_contract_id,
                        "error": str(exc),
                    },
                )
                break

            current_evidence = retrieved
            evidence.extend(retrieved)
            context.record_evidence(step.step_index, current_evidence)
            record_evidence(retrieved)
            enforce_entropy_authorization()
            try:
                context.consume_budget(artifacts=0)
                context.consume_evidence_budget(len(retrieved))
            except Exception as exc:
                record_event(
                    EventType.RETRIEVAL_FAILED,
                    step.step_index,
                    {
                        "step_index": step.step_index,
                        "request_id": step.retrieval_request.request_id,
                        "vector_contract_id": step.retrieval_request.vector_contract_id,
                        "error": str(exc),
                    },
                )
                break
            try:
                for item in retrieved:
                    context.artifact_store.create(
                        spec_version="v1",
                        artifact_id=ArtifactID(
                            f"evidence-{step.step_index}-{item.evidence_id}"
                        ),
                        tenant_id=context.tenant_id,
                        artifact_type=ArtifactType.RETRIEVED_EVIDENCE,
                        producer="retrieval",
                        parent_artifacts=(),
                        content_hash=item.content_hash,
                        scope=ArtifactScope.AUDIT,
                    )
            except Exception as exc:
                record_event(
                    EventType.RETRIEVAL_FAILED,
                    step.step_index,
                    {
                        "step_index": step.step_index,
                        "request_id": step.retrieval_request.request_id,
                        "vector_contract_id": step.retrieval_request.vector_contract_id,
                        "error": str(exc),
                    },
                )
                break

            output_fingerprint = fingerprint_inputs(
                [
                    {
                        "evidence_id": item.evidence_id,
                        "content_hash": item.content_hash,
                    }
                    for item in retrieved
                ]
            )
            input_fingerprint = pending_invocations.pop(
                (step.step_index, tool_retrieval),
                ContentHash(fingerprint_inputs(tool_input)),
            )
            record_tool_invocation(
                ToolInvocation(
                    spec_version="v1",
                    tool_id=tool_retrieval,
                    determinism_level=step.determinism_level,
                    inputs_fingerprint=input_fingerprint,
                    outputs_fingerprint=ContentHash(output_fingerprint),
                    duration=0.0,
                    outcome="success",
                )
            )
            record_event(
                EventType.TOOL_CALL_END,
                step.step_index,
                {
                    "tool_id": tool_retrieval,
                    "input_fingerprint": fingerprint_inputs(tool_input),
                    "output_fingerprint": output_fingerprint,
                },
            )

            record_event(
                EventType.RETRIEVAL_END,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "request_id": step.retrieval_request.request_id,
                    "vector_contract_id": step.retrieval_request.vector_contract_id,
                    "evidence_hashes": [item.content_hash for item in retrieved],
                },
            )

        # Phase: agent execution.
        tool_input = {
            "tool_id": tool_agent,
            "agent_id": step.agent_id,
            "inputs_fingerprint": step.inputs_fingerprint,
            "evidence_ids": [item.evidence_id for item in current_evidence],
        }
        record_event(
            EventType.TOOL_CALL_START,
            step.step_index,
            {
                "tool_id": tool_agent,
                "input_fingerprint": fingerprint_inputs(tool_input),
            },
        )
        pending_invocations[(step.step_index, tool_agent)] = ContentHash(
            fingerprint_inputs(tool_input)
        )
        step_artifacts: list[Artifact] = []
        try:
            step_artifacts = agent_executor.execute(step, context)
            artifacts.extend(step_artifacts)
            record_artifacts(step_artifacts)
            validate_outputs(StepType.AGENT, step_artifacts, current_evidence)
            context.consume_budget(artifacts=len(step_artifacts))
            context.consume_step_artifacts(len(step_artifacts))
        except Exception as exc:
            input_fingerprint = pending_invocations.pop(
                (step.step_index, tool_agent),
                ContentHash(fingerprint_inputs(tool_input)),
            )
            record_tool_invocation(
                ToolInvocation(
                    spec_version="v1",
                    tool_id=tool_agent,
                    determinism_level=step.determinism_level,
                    inputs_fingerprint=input_fingerprint,
                    outputs_fingerprint=None,
                    duration=0.0,
                    outcome="fail",
                )
            )
            record_event(
                EventType.TOOL_CALL_FAIL,
                step.step_index,
                {
                    "tool_id": tool_agent,
                    "input_fingerprint": fingerprint_inputs(tool_input),
                    "error": str(exc),
                },
            )
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

        output_fingerprint = fingerprint_inputs(
            [
                {
                    "artifact_id": item.artifact_id,
                    "content_hash": item.content_hash,
                }
                for item in step_artifacts
            ]
        )
        input_fingerprint = pending_invocations.pop(
            (step.step_index, tool_agent),
            ContentHash(fingerprint_inputs(tool_input)),
        )
        record_tool_invocation(
            ToolInvocation(
                spec_version="v1",
                tool_id=tool_agent,
                determinism_level=step.determinism_level,
                inputs_fingerprint=input_fingerprint,
                outputs_fingerprint=ContentHash(output_fingerprint),
                duration=0.0,
                outcome="success",
            )
        )
        record_event(
            EventType.TOOL_CALL_END,
            step.step_index,
            {
                "tool_id": tool_agent,
                "input_fingerprint": fingerprint_inputs(tool_input),
                "output_fingerprint": output_fingerprint,
            },
        )

        # Phase: forced verification override.
        forced_action = handle_verification_phase_override(
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

        # Phase: reasoning.
        record_event(
            EventType.REASONING_START,
            step.step_index,
            {
                "step_index": step.step_index,
                "agent_id": step.agent_id,
            },
        )
        tool_input = {
            "tool_id": tool_reasoning,
            "agent_id": step.agent_id,
            "artifact_ids": [artifact.artifact_id for artifact in step_artifacts],
            "evidence_ids": [item.evidence_id for item in current_evidence],
        }
        # Phase: verification.
        record_event(
            EventType.TOOL_CALL_START,
            step.step_index,
            {
                "tool_id": tool_reasoning,
                "input_fingerprint": fingerprint_inputs(tool_input),
            },
        )
        pending_invocations[(step.step_index, tool_reasoning)] = ContentHash(
            fingerprint_inputs(tool_input)
        )

        try:
            bundle = reasoning_executor.execute(step, context)
            reasoning_bundles.append(bundle)
            bundle_hash = ContentHash(reasoning_executor.bundle_hash(bundle))

            evidence_ids = {item.evidence_id for item in current_evidence}
            for claim in bundle.claims:
                if any(
                    evidence_id not in evidence_ids
                    for evidence_id in claim.supported_by
                ):
                    raise ValueError("reasoning claim references unknown evidence")

            record_event(
                EventType.TOOL_CALL_END,
                step.step_index,
                {
                    "tool_id": tool_reasoning,
                    "input_fingerprint": fingerprint_inputs(tool_input),
                    "output_fingerprint": fingerprint_inputs(
                        {"bundle_hash": bundle_hash}
                    ),
                },
            )
            input_fingerprint = pending_invocations.pop(
                (step.step_index, tool_reasoning),
                ContentHash(fingerprint_inputs(tool_input)),
            )
            record_tool_invocation(
                ToolInvocation(
                    spec_version="v1",
                    tool_id=tool_reasoning,
                    determinism_level=step.determinism_level,
                    inputs_fingerprint=input_fingerprint,
                    outputs_fingerprint=ContentHash(
                        fingerprint_inputs({"bundle_hash": bundle_hash})
                    ),
                    duration=0.0,
                    outcome="success",
                )
            )
            record_event(
                EventType.REASONING_END,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "bundle_hash": bundle_hash,
                    "claim_count": len(bundle.claims),
                },
            )
            record_claims(tuple(claim.claim_id for claim in bundle.claims))

            artifacts.append(
                context.artifact_store.create(
                    spec_version="v1",
                    artifact_id=bundle.bundle_id,
                    tenant_id=context.tenant_id,
                    artifact_type=ArtifactType.REASONING_BUNDLE,
                    producer="reasoning",
                    parent_artifacts=tuple(
                        artifact.artifact_id for artifact in step_artifacts
                    ),
                    content_hash=bundle_hash,
                    scope=ArtifactScope.AUDIT,
                )
            )
            record_artifacts([artifacts[-1]])
            context.consume_budget(
                artifacts=1,
                tokens=sum(len(claim.statement.split()) for claim in bundle.claims),
            )
            context.consume_step_artifacts(1)
            validate_outputs(
                StepType.REASONING,
                [artifacts[-1]],
                current_evidence,
            )
        except Exception as exc:
            input_fingerprint = pending_invocations.pop(
                (step.step_index, tool_reasoning),
                ContentHash(fingerprint_inputs(tool_input)),
            )
            record_tool_invocation(
                ToolInvocation(
                    spec_version="v1",
                    tool_id=tool_reasoning,
                    determinism_level=step.determinism_level,
                    inputs_fingerprint=input_fingerprint,
                    outputs_fingerprint=None,
                    duration=0.0,
                    outcome="fail",
                )
            )
            record_event(
                EventType.TOOL_CALL_FAIL,
                step.step_index,
                {
                    "tool_id": tool_reasoning,
                    "input_fingerprint": fingerprint_inputs(tool_input),
                    "error": str(exc),
                },
            )
            record_event(
                EventType.REASONING_FAILED,
                step.step_index,
                {
                    "step_index": step.step_index,
                    "agent_id": step.agent_id,
                    "error": str(exc),
                },
            )
            break

        # Phase exit: step completion.
        record_event(
            EventType.VERIFICATION_START,
            step.step_index,
            {"step_index": step.step_index},
        )

        try:
            stored_artifacts = [
                context.artifact_store.load(
                    item.artifact_id, tenant_id=context.tenant_id
                )
                for item in step_artifacts
            ]
        except Exception as exc:
            verification_results.append(
                VerificationResult(
                    spec_version="v1",
                    engine_id="integrity",
                    status="FAIL",
                    reason="artifact_store_integrity",
                    randomness=VerificationRandomness.DETERMINISTIC,
                    violations=(RuleID("artifact_store_integrity"),),
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
                    "rule_ids": ["artifact_store_integrity"],
                    "error": str(exc),
                },
            )
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

        results, arbitration = verification_orchestrator.verify_bundle(
            bundle, current_evidence, stored_artifacts, policy
        )
        verification_results.extend(results)
        verification_arbitrations.append(arbitration)
        status_to_event = {
            "PASS": EventType.VERIFICATION_PASS,
            "FAIL": EventType.VERIFICATION_FAIL,
            "ESCALATE": EventType.VERIFICATION_ESCALATE,
        }
        record_event(
            status_to_event[arbitration.decision],
            step.step_index,
            {
                "step_index": step.step_index,
                "status": arbitration.decision,
                "rule_ids": [
                    violation for result in results for violation in result.violations
                ],
            },
        )
        record_event(
            EventType.VERIFICATION_ARBITRATION,
            step.step_index,
            {
                "step_index": step.step_index,
                "decision": arbitration.decision,
                "engine_ids": arbitration.engine_ids,
                "engine_statuses": arbitration.engine_statuses,
            },
        )

        if arbitration.decision != "PASS":
            if context.mode == RunMode.UNSAFE:
                record_event(
                    EventType.SEMANTIC_VIOLATION,
                    step.step_index,
                    {
                        "step_index": step.step_index,
                        "decision": arbitration.decision,
                        "rule_ids": [
                            violation
                            for result in results
                            for violation in result.violations
                        ],
                    },
                )
            else:
                break

        record_event(
            EventType.STEP_END,
            step.step_index,
            {
                "step_index": step.step_index,
                "agent_id": step.agent_id,
            },
        )
        enforce_entropy_authorization()
        flush_entropy_usage()
        save_checkpoint(step.step_index)
        crash_step = os.environ.get("AF_CRASH_AT_STEP")
        if crash_step is not None and int(crash_step) == step.step_index:
            os.kill(os.getpid(), signal.SIGKILL)

    # Phase exit: flow-level verification.
    if not interrupted and policy is not None and reasoning_bundles:
        flow_results, flow_arbitration = verification_orchestrator.verify_flow(
            reasoning_bundles, policy
        )
        verification_results.extend(flow_results)
        verification_arbitrations.append(flow_arbitration)
        record_event(
            EventType.VERIFICATION_ARBITRATION,
            steps_plan.steps[-1].step_index if steps_plan.steps else 0,
            {
                "step_index": steps_plan.steps[-1].step_index
                if steps_plan.steps
                else 0,
                "decision": flow_arbitration.decision,
                "engine_ids": flow_arbitration.engine_ids,
                "engine_statuses": flow_arbitration.engine_statuses,
            },
        )
    return interrupted


def _causality_tag(event_type: EventType) -> CausalityTag:
    """Internal helper; not part of the public API."""
    if event_type in {
        EventType.RETRIEVAL_START,
        EventType.RETRIEVAL_END,
        EventType.RETRIEVAL_FAILED,
    }:
        return CausalityTag.DATASET
    if event_type in {EventType.TOOL_CALL_START, EventType.TOOL_CALL_END}:
        return CausalityTag.TOOL
    if event_type in {EventType.STEP_START, EventType.STEP_END}:
        return CausalityTag.AGENT
    if event_type in {
        EventType.VERIFICATION_START,
        EventType.VERIFICATION_PASS,
        EventType.VERIFICATION_FAIL,
        EventType.VERIFICATION_ESCALATE,
        EventType.VERIFICATION_ARBITRATION,
    }:
        return CausalityTag.TOOL
    if event_type in {EventType.STEP_FAILED, EventType.VERIFICATION_FAIL}:
        return CausalityTag.AGENT
    if event_type in {EventType.EXECUTION_INTERRUPTED, EventType.SEMANTIC_VIOLATION}:
        return CausalityTag.ENVIRONMENT
    return CausalityTag.AGENT


__all__ = ["execution_phase", "execute_step_phase"]
