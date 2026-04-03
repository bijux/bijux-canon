# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import bijux_agent
import bijux_rar
import pytest

from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.model.artifact.reasoning_claim import ReasoningClaim
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.reasoning_step import ReasoningStep
from agentic_flows.spec.ontology import (
    ArtifactType,
    DeterminismLevel,
    FlowState,
    StepType,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    BundleID,
    ClaimID,
    ContractID,
    EvidenceID,
    FlowID,
    GateID,
    InputsFingerprint,
    StepID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EventType,
    ReplayAcceptability,
)

pytestmark = pytest.mark.e2e


def test_reasoning_references_missing_evidence(
    baseline_policy,
    resolved_flow_factory,
    entropy_budget,
    replay_envelope,
    dataset_descriptor,
    execution_store,
) -> None:
    bijux_agent.run = lambda **_kwargs: [
        {
            "artifact_id": "agent-output",
            "artifact_type": ArtifactType.AGENT_INVOCATION.value,
            "content": "payload",
            "parent_artifacts": [],
        }
    ]

    def _bad_reason(**_kwargs):
        return ReasoningBundle(
            spec_version="v1",
            bundle_id=BundleID("bundle-1"),
            claims=(
                ReasoningClaim(
                    spec_version="v1",
                    claim_id=ClaimID("claim-1"),
                    statement="statement",
                    confidence=0.5,
                    supported_by=(EvidenceID("missing-evidence"),),
                ),
            ),
            steps=(
                ReasoningStep(
                    spec_version="v1",
                    step_id=StepID("step-1"),
                    input_claims=(),
                    output_claims=(ClaimID("claim-1"),),
                    method="deduction",
                ),
            ),
            evidence_ids=(EvidenceID("missing-evidence"),),
            producer_agent_id=AgentID("agent-a"),
        )

    bijux_rar.reason = _bad_reason

    step = ResolvedStep(
        spec_version="v1",
        step_index=0,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID("agent-a"),
        inputs_fingerprint=InputsFingerprint("inputs"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-a"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=None,
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-reasoning"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    resolved_flow = resolved_flow_factory(manifest, (step,))

    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )
    trace = result.trace

    assert result.evidence == []
    assert any(event.event_type == EventType.REASONING_FAILED for event in trace.events)
    assert trace.events[-1].event_type in {
        EventType.REASONING_FAILED,
        EventType.VERIFICATION_ARBITRATION,
    }
