# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verification helpers for runtime step execution."""

from __future__ import annotations

from typing import Protocol

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.execution.resolved_step import ResolvedStep
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.ontology import VerificationPhase, VerificationRandomness
from bijux_canon_runtime.ontology.ids import RuleID
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.context import ExecutionContext


class VerificationCallbacks(Protocol):
    """Callback contract used by step verification."""

    def record_event(
        self, event_type: EventType, step_index: int, payload: dict[str, object]
    ) -> None:
        """Record a runtime event."""
        ...

    def enforce_entropy_authorization(self) -> None:
        """Enforce entropy authorization after verification."""
        ...

    def flush_entropy_usage(self) -> None:
        """Flush persisted entropy usage."""
        ...

    def save_checkpoint(self, step_index: int) -> None:
        """Persist a checkpoint after a successful step."""
        ...


class VerificationOrchestratorLike(Protocol):
    """Verification orchestrator contract used by step verification."""

    def verify_bundle(
        self,
        reasoning: ReasoningBundle,
        evidence: list[RetrievedEvidence],
        artifacts: list[Artifact],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Verify the current reasoning bundle."""
        ...

    def verify_flow(
        self,
        reasoning_bundles: list[ReasoningBundle],
        policy: VerificationPolicy,
    ) -> tuple[list[VerificationResult], VerificationArbitration]:
        """Verify flow-level reasoning results."""
        ...


class VerificationServices(Protocol):
    """Service contract used by step verification."""

    @property
    def policy(self) -> VerificationPolicy | None:
        """Return the active verification policy."""
        ...

    @property
    def verification_orchestrator(self) -> VerificationOrchestratorLike:
        """Return the verification orchestrator."""
        ...


def verify_step_outcome(
    *,
    step: ResolvedStep,
    context: ExecutionContext,
    callbacks: VerificationCallbacks,
    services: VerificationServices,
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
        _record_artifact_store_integrity_failure(
            step=step,
            callbacks=callbacks,
            verification_results=verification_results,
            step_artifacts=step_artifacts,
            error=exc,
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
    callbacks: VerificationCallbacks,
    services: VerificationServices,
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


def _record_artifact_store_integrity_failure(
    *,
    step: ResolvedStep,
    callbacks: VerificationCallbacks,
    verification_results: list[VerificationResult],
    step_artifacts: list[Artifact],
    error: Exception,
) -> None:
    """Record artifact-store integrity failures as verification failures."""
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
            "error": str(error),
        },
    )
    callbacks.record_event(
        EventType.STEP_FAILED,
        step.step_index,
        {
            "step_index": step.step_index,
            "agent_id": step.agent_id,
            "error": str(error),
        },
    )


__all__ = ["record_flow_verification", "verify_step_outcome"]
