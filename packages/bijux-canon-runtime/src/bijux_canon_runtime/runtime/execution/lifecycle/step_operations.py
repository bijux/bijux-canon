# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Step-level execution helpers for the runtime lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from bijux_canon_runtime.contracts.step_contract import validate_outputs
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.execution.resolved_step import ResolvedStep
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.observability.classification.retrieval_fingerprint import (
    fingerprint_retrieval,
)
from bijux_canon_runtime.ontology import (
    ArtifactScope,
    ArtifactType,
    StepType,
    VerificationPhase,
    VerificationRandomness,
)
from bijux_canon_runtime.ontology.ids import (
    ArtifactID,
    ClaimID,
    ContentHash,
    RuleID,
    ToolID,
)
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.context import ExecutionContext, RunMode
from bijux_canon_runtime.runtime.execution.agent_executor import AgentExecutor
from bijux_canon_runtime.runtime.execution.lifecycle.tool_event_recording import (
    record_tool_failure,
    record_tool_success,
)
from bijux_canon_runtime.runtime.execution.reasoning_executor import ReasoningExecutor
from bijux_canon_runtime.runtime.execution.retrieval_executor import RetrievalExecutor
from bijux_canon_runtime.verification.orchestrator import VerificationOrchestrator


@dataclass(frozen=True)
class StepCallbacks:
    """Runtime callbacks used while executing a single step."""

    record_event: Callable[[EventType, int, dict[str, object]], None]
    record_tool_invocation: Callable[[ToolInvocation], None]
    record_evidence: Callable[[list[RetrievedEvidence]], None]
    record_artifacts: Callable[[list[Artifact]], None]
    record_claims: Callable[[tuple[ClaimID, ...]], None]
    flush_entropy_usage: Callable[[], None]
    enforce_entropy_authorization: Callable[[], None]
    save_checkpoint: Callable[[int], None]


@dataclass(frozen=True)
class StepServices:
    """Runtime services used while executing a single step."""

    agent_executor: AgentExecutor
    retrieval_executor: RetrievalExecutor
    reasoning_executor: ReasoningExecutor
    verification_orchestrator: VerificationOrchestrator
    policy: VerificationPolicy | None
    tool_agent: ToolID
    tool_retrieval: ToolID
    tool_reasoning: ToolID
    handle_verification_override: VerificationOverrideHandler


class VerificationOverrideHandler(Protocol):
    """Verification override callback contract."""

    def __call__(
        self,
        *,
        step: ResolvedStep,
        context: ExecutionContext,
        record_event: Callable[[EventType, int, dict[str, object]], None],
        verification_results: list[VerificationResult],
        step_artifacts: list[Artifact],
    ) -> str | None:
        """Return an override action for the current step."""
        ...


def execute_retrieval_step(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    callbacks: StepCallbacks,
    services: StepServices,
    evidence: list[RetrievedEvidence],
    pending_invocations: dict[tuple[int, ToolID], ContentHash],
) -> tuple[bool, list[RetrievedEvidence]]:
    """Run retrieval work for a step and return whether execution should stop."""
    if step.retrieval_request is None:
        return False, []
    request_fingerprint = fingerprint_retrieval(step.retrieval_request)
    callbacks.record_event(
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
        "tool_id": services.tool_retrieval,
        "request_id": step.retrieval_request.request_id,
        "vector_contract_id": step.retrieval_request.vector_contract_id,
        "request_fingerprint": request_fingerprint,
    }
    input_fingerprint = ContentHash(fingerprint_inputs(tool_input))
    callbacks.record_event(
        EventType.TOOL_CALL_START,
        step.step_index,
        {
            "tool_id": services.tool_retrieval,
            "input_fingerprint": input_fingerprint,
        },
    )
    pending_invocations[(step.step_index, services.tool_retrieval)] = input_fingerprint
    try:
        retrieved = services.retrieval_executor.execute(step, context)
    except Exception as exc:
        record_tool_failure(
            step_index=step.step_index,
            tool_id=services.tool_retrieval,
            determinism_level=step.determinism_level,
            tool_input=tool_input,
            pending_invocations=pending_invocations,
            callbacks=callbacks,
            error=exc,
            failure_event=EventType.RETRIEVAL_FAILED,
            failure_payload={
                "step_index": step.step_index,
                "request_id": step.retrieval_request.request_id,
                "vector_contract_id": step.retrieval_request.vector_contract_id,
                "error": str(exc),
            },
        )
        return True, []

    evidence.extend(retrieved)
    context.record_evidence(step.step_index, retrieved)
    callbacks.record_evidence(retrieved)
    callbacks.enforce_entropy_authorization()
    try:
        context.consume_budget(artifacts=0)
        context.consume_evidence_budget(len(retrieved))
        _persist_retrieval_artifacts(step=step, context=context, retrieved=retrieved)
    except Exception as exc:
        callbacks.record_event(
            EventType.RETRIEVAL_FAILED,
            step.step_index,
            {
                "step_index": step.step_index,
                "request_id": step.retrieval_request.request_id,
                "vector_contract_id": step.retrieval_request.vector_contract_id,
                "error": str(exc),
            },
        )
        return True, retrieved

    output_fingerprint = fingerprint_inputs(
        [
            {
                "evidence_id": item.evidence_id,
                "content_hash": item.content_hash,
            }
            for item in retrieved
        ]
    )
    record_tool_success(
        step_index=step.step_index,
        tool_id=services.tool_retrieval,
        determinism_level=step.determinism_level,
        tool_input=tool_input,
        output_fingerprint=output_fingerprint,
        pending_invocations=pending_invocations,
        callbacks=callbacks,
    )
    callbacks.record_event(
        EventType.RETRIEVAL_END,
        step.step_index,
        {
            "step_index": step.step_index,
            "request_id": step.retrieval_request.request_id,
            "vector_contract_id": step.retrieval_request.vector_contract_id,
            "evidence_hashes": [item.content_hash for item in retrieved],
        },
    )
    return False, retrieved


def execute_agent_step(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    callbacks: StepCallbacks,
    services: StepServices,
    artifacts: list[Artifact],
    current_evidence: list[RetrievedEvidence],
    pending_invocations: dict[tuple[int, ToolID], ContentHash],
) -> tuple[bool, list[Artifact]]:
    """Run agent work for a step and return whether execution should stop."""
    tool_input = {
        "tool_id": services.tool_agent,
        "agent_id": step.agent_id,
        "inputs_fingerprint": step.inputs_fingerprint,
        "evidence_ids": [item.evidence_id for item in current_evidence],
    }
    callbacks.record_event(
        EventType.TOOL_CALL_START,
        step.step_index,
        {
            "tool_id": services.tool_agent,
            "input_fingerprint": fingerprint_inputs(tool_input),
        },
    )
    pending_invocations[(step.step_index, services.tool_agent)] = ContentHash(
        fingerprint_inputs(tool_input)
    )
    try:
        step_artifacts = services.agent_executor.execute(step, context)
        artifacts.extend(step_artifacts)
        callbacks.record_artifacts(step_artifacts)
        validate_outputs(StepType.AGENT, step_artifacts, current_evidence)
        context.consume_budget(artifacts=len(step_artifacts))
        context.consume_step_artifacts(len(step_artifacts))
    except Exception as exc:
        record_tool_failure(
            step_index=step.step_index,
            tool_id=services.tool_agent,
            determinism_level=step.determinism_level,
            tool_input=tool_input,
            pending_invocations=pending_invocations,
            callbacks=callbacks,
            error=exc,
            failure_event=EventType.STEP_FAILED,
            failure_payload={
                "step_index": step.step_index,
                "agent_id": step.agent_id,
                "error": str(exc),
            },
        )
        return True, []

    output_fingerprint = fingerprint_inputs(
        [
            {
                "artifact_id": item.artifact_id,
                "content_hash": item.content_hash,
            }
            for item in step_artifacts
        ]
    )
    record_tool_success(
        step_index=step.step_index,
        tool_id=services.tool_agent,
        determinism_level=step.determinism_level,
        tool_input=tool_input,
        output_fingerprint=output_fingerprint,
        pending_invocations=pending_invocations,
        callbacks=callbacks,
    )
    return False, step_artifacts


def execute_reasoning_step(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    callbacks: StepCallbacks,
    services: StepServices,
    artifacts: list[Artifact],
    current_evidence: list[RetrievedEvidence],
    step_artifacts: list[Artifact],
    pending_invocations: dict[tuple[int, ToolID], ContentHash],
    reasoning_bundles: list[ReasoningBundle],
) -> tuple[bool, ReasoningBundle | None]:
    """Run reasoning work for a step and return whether execution should stop."""
    callbacks.record_event(
        EventType.REASONING_START,
        step.step_index,
        {
            "step_index": step.step_index,
            "agent_id": step.agent_id,
        },
    )
    tool_input = {
        "tool_id": services.tool_reasoning,
        "agent_id": step.agent_id,
        "artifact_ids": [artifact.artifact_id for artifact in step_artifacts],
        "evidence_ids": [item.evidence_id for item in current_evidence],
    }
    callbacks.record_event(
        EventType.TOOL_CALL_START,
        step.step_index,
        {
            "tool_id": services.tool_reasoning,
            "input_fingerprint": fingerprint_inputs(tool_input),
        },
    )
    pending_invocations[(step.step_index, services.tool_reasoning)] = ContentHash(
        fingerprint_inputs(tool_input)
    )
    try:
        bundle = services.reasoning_executor.execute(step, context)
        reasoning_bundles.append(bundle)
        bundle_hash = ContentHash(services.reasoning_executor.bundle_hash(bundle))
        _validate_bundle_evidence(bundle=bundle, current_evidence=current_evidence)
        output_fingerprint = fingerprint_inputs({"bundle_hash": bundle_hash})
        record_tool_success(
            step_index=step.step_index,
            tool_id=services.tool_reasoning,
            determinism_level=step.determinism_level,
            tool_input=tool_input,
            output_fingerprint=output_fingerprint,
            pending_invocations=pending_invocations,
            callbacks=callbacks,
        )
        callbacks.record_event(
            EventType.REASONING_END,
            step.step_index,
            {
                "step_index": step.step_index,
                "bundle_hash": bundle_hash,
                "claim_count": len(bundle.claims),
            },
        )
        callbacks.record_claims(tuple(claim.claim_id for claim in bundle.claims))
        reasoning_artifact = context.artifact_store.create(
            spec_version="v1",
            artifact_id=ArtifactID(str(bundle.bundle_id)),
            tenant_id=context.tenant_id,
            artifact_type=ArtifactType.REASONING_BUNDLE,
            producer="reasoning",
            parent_artifacts=tuple(artifact.artifact_id for artifact in step_artifacts),
            content_hash=bundle_hash,
            scope=ArtifactScope.AUDIT,
        )
        artifacts.append(reasoning_artifact)
        callbacks.record_artifacts([reasoning_artifact])
        context.consume_budget(
            artifacts=1,
            tokens=sum(len(claim.statement.split()) for claim in bundle.claims),
        )
        context.consume_step_artifacts(1)
        validate_outputs(StepType.REASONING, [reasoning_artifact], current_evidence)
        return False, bundle
    except Exception as exc:
        record_tool_failure(
            step_index=step.step_index,
            tool_id=services.tool_reasoning,
            determinism_level=step.determinism_level,
            tool_input=tool_input,
            pending_invocations=pending_invocations,
            callbacks=callbacks,
            error=exc,
            failure_event=EventType.REASONING_FAILED,
            failure_payload={
                "step_index": step.step_index,
                "agent_id": step.agent_id,
                "error": str(exc),
            },
        )
        return True, None


def verify_step_outcome(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    callbacks: StepCallbacks,
    services: StepServices,
    current_evidence: list[RetrievedEvidence],
    step_artifacts: list[Artifact],
    bundle: ReasoningBundle,
    verification_results: list[VerificationResult],
    verification_arbitrations: list[VerificationArbitration],
) -> bool:
    """Verify step outputs and return whether execution should stop."""
    policy = services.policy
    if policy is None:
        raise ValueError("verification policy is required for step verification")
    callbacks.record_event(
        EventType.VERIFICATION_START,
        step.step_index,
        {"step_index": step.step_index},
    )
    try:
        stored_artifacts = [
            context.artifact_store.load(item.artifact_id, tenant_id=context.tenant_id)
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
        callbacks.record_event(
            EventType.VERIFICATION_FAIL,
            step.step_index,
            {
                "step_index": step.step_index,
                "status": "FAIL",
                "rule_ids": ["artifact_store_integrity"],
                "error": str(exc),
            },
        )
        callbacks.record_event(
            EventType.STEP_FAILED,
            step.step_index,
            {
                "step_index": step.step_index,
                "agent_id": step.agent_id,
                "error": str(exc),
            },
        )
        return True

    results, arbitration = services.verification_orchestrator.verify_bundle(
        bundle, current_evidence, stored_artifacts, policy
    )
    verification_results.extend(results)
    verification_arbitrations.append(arbitration)
    status_to_event = {
        "PASS": EventType.VERIFICATION_PASS,
        "FAIL": EventType.VERIFICATION_FAIL,
        "ESCALATE": EventType.VERIFICATION_ESCALATE,
    }
    callbacks.record_event(
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
    callbacks.record_event(
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
            callbacks.record_event(
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
            return False
        return True
    callbacks.record_event(
        EventType.STEP_END,
        step.step_index,
        {
            "step_index": step.step_index,
            "agent_id": step.agent_id,
        },
    )
    callbacks.enforce_entropy_authorization()
    callbacks.flush_entropy_usage()
    callbacks.save_checkpoint(step.step_index)
    return False


def record_flow_verification(
    *,
    steps_plan: ExecutionSteps,
    callbacks: StepCallbacks,
    services: StepServices,
    reasoning_bundles: list[ReasoningBundle],
    verification_results: list[VerificationResult],
    verification_arbitrations: list[VerificationArbitration],
) -> None:
    """Record flow-level verification after step execution completes."""
    if services.policy is None or not reasoning_bundles:
        return
    flow_results, flow_arbitration = services.verification_orchestrator.verify_flow(
        reasoning_bundles, services.policy
    )
    verification_results.extend(flow_results)
    verification_arbitrations.append(flow_arbitration)
    step_index = steps_plan.steps[-1].step_index if steps_plan.steps else 0
    callbacks.record_event(
        EventType.VERIFICATION_ARBITRATION,
        step_index,
        {
            "step_index": step_index,
            "decision": flow_arbitration.decision,
            "engine_ids": flow_arbitration.engine_ids,
            "engine_statuses": flow_arbitration.engine_statuses,
        },
    )


def _persist_retrieval_artifacts(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    retrieved: list[RetrievedEvidence],
) -> None:
    """Create audit artifacts for retrieved evidence."""
    for item in retrieved:
        context.artifact_store.create(
            spec_version="v1",
            artifact_id=ArtifactID(f"evidence-{step.step_index}-{item.evidence_id}"),
            tenant_id=context.tenant_id,
            artifact_type=ArtifactType.RETRIEVED_EVIDENCE,
            producer="retrieval",
            parent_artifacts=(),
            content_hash=item.content_hash,
            scope=ArtifactScope.AUDIT,
        )


def _validate_bundle_evidence(
    *,
    bundle: ReasoningBundle,
    current_evidence: list[RetrievedEvidence],
) -> None:
    """Ensure reasoning claims only reference evidence seen in the current step."""
    evidence_ids = {item.evidence_id for item in current_evidence}
    for claim in bundle.claims:
        if any(evidence_id not in evidence_ids for evidence_id in claim.supported_by):
            raise ValueError("reasoning claim references unknown evidence")


__all__ = [
    "StepCallbacks",
    "StepServices",
    "VerificationOverrideHandler",
    "execute_agent_step",
    "execute_reasoning_step",
    "execute_retrieval_step",
    "record_flow_verification",
    "verify_step_outcome",
]
