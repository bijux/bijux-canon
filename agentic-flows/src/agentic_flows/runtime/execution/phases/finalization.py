# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Finalization phase helpers for LiveExecutor."""

from __future__ import annotations

from agentic_flows.core.authority import finalize_trace
from agentic_flows.core.errors import ExecutionFailure
from agentic_flows.runtime.context import ExecutionContext
from agentic_flows.runtime.execution.step_executor import ExecutionOutcome
from agentic_flows.runtime.observability.analysis.flow_invariants import (
    validate_flow_invariants,
)
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_policy,
)
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.ontology.ids import PolicyFingerprint, ResolverID


def finalization_phase(
    *,
    steps_plan,
    context: ExecutionContext,
    state,
    resolver_id_from_metadata,
) -> ExecutionOutcome:
    """Internal helper; not part of the public API."""
    if state.interrupted:
        raise ExecutionFailure("execution interrupted")

    validate_flow_invariants(context, state.artifacts)

    resolver_id = ResolverID(resolver_id_from_metadata(steps_plan.resolution_metadata))
    claim_ids = list(context.initial_claim_ids)
    claim_ids.extend(
        claim.claim_id for bundle in state.reasoning_bundles for claim in bundle.claims
    )
    contradiction_count = sum(
        1
        for result in state.verification_results
        if result.engine_id == "contradiction" and result.status == "FAIL"
    )
    arbitration_decision = (
        state.verification_arbitrations[-1].decision
        if state.verification_arbitrations
        else "none"
    )
    nondeterminism_verdict = context.entropy.verdict()
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=steps_plan.flow_id,
        tenant_id=steps_plan.tenant_id,
        parent_flow_id=context.parent_flow_id,
        child_flow_ids=context.child_flow_ids,
        flow_state=steps_plan.flow_state,
        determinism_level=steps_plan.determinism_level,
        replay_mode=steps_plan.replay_mode,
        replay_acceptability=steps_plan.replay_acceptability,
        dataset=steps_plan.dataset,
        replay_envelope=steps_plan.replay_envelope,
        allow_deprecated_datasets=steps_plan.allow_deprecated_datasets,
        environment_fingerprint=steps_plan.environment_fingerprint,
        plan_hash=steps_plan.plan_hash,
        verification_policy_fingerprint=(
            PolicyFingerprint(fingerprint_policy(context.verification_policy))
            if context.verification_policy is not None
            else None
        ),
        resolver_id=resolver_id,
        events=state.recorder.events(),
        tool_invocations=tuple(state.tool_invocations),
        entropy_usage=context.entropy_usage(),
        claim_ids=tuple(dict.fromkeys(claim_ids)),
        contradiction_count=contradiction_count,
        arbitration_decision=arbitration_decision,
        entropy_exhausted=nondeterminism_verdict.entropy_exhausted,
        entropy_exhaustion_action=nondeterminism_verdict.entropy_exhaustion_action,
        non_certifiable=nondeterminism_verdict.non_certifiable,
        finalized=False,
    )
    finalize_trace(trace)
    return ExecutionOutcome(
        trace=trace,
        artifacts=state.artifacts,
        evidence=state.evidence,
        reasoning_bundles=state.reasoning_bundles,
        verification_results=state.verification_results,
        verification_arbitrations=state.verification_arbitrations,
    )


__all__ = ["finalization_phase"]
