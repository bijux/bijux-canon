# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import bijux_agent
import bijux_rag
import bijux_rar
import bijux_vex
import pytest

from agentic_flows.runtime.artifact_store import HostileArtifactStore
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.model.artifact.reasoning_claim import ReasoningClaim
from agentic_flows.spec.model.datasets.retrieval_request import RetrievalRequest
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.reasoning_step import ReasoningStep
from agentic_flows.spec.ontology import (
    ArtifactType,
    DeterminismLevel,
    EvidenceDeterminism,
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
    RequestID,
    StepID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EventType,
    ReplayAcceptability,
)
from tests.helpers import build_claim_statement

pytestmark = pytest.mark.regression


def test_hostile_artifact_store_triggers_verification_failure(
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
    bijux_rag.retrieve = lambda **_kwargs: [
        {
            "evidence_id": "ev-1",
            "determinism": EvidenceDeterminism.DETERMINISTIC.value,
            "source_uri": "file://doc",
            "content": "content",
            "score": 0.9,
            "vector_contract_id": "contract-1",
        }
    ]
    bijux_vex.enforce_contract = lambda *_args, **_kwargs: True

    def _reason(agent_outputs, evidence, seed):
        statement = build_claim_statement(agent_outputs, evidence)
        return ReasoningBundle(
            spec_version="v1",
            bundle_id=BundleID("bundle-1"),
            claims=(
                ReasoningClaim(
                    spec_version="v1",
                    claim_id=ClaimID("claim-1"),
                    statement=statement,
                    confidence=0.5,
                    supported_by=(EvidenceID("ev-1"),),
                ),
            ),
            steps=(
                ReasoningStep(
                    spec_version="v1",
                    step_id=StepID("step-1"),
                    input_claims=(),
                    output_claims=(ClaimID("claim-1"),),
                    method="aggregation",
                ),
            ),
            evidence_ids=(EvidenceID("ev-1"),),
            producer_agent_id=AgentID("agent-a"),
        )

    bijux_rar.reason = _reason

    request = RetrievalRequest(
        spec_version="v1",
        request_id=RequestID("req-1"),
        query="query",
        vector_contract_id=ContractID("contract-1"),
        top_k=1,
        scope="project",
    )
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
        retrieval_request=request,
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-hostile"),
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
        retrieval_contracts=(ContractID("contract-1"),),
        verification_gates=(GateID("gate-a"),),
    )
    resolved_flow = resolved_flow_factory(manifest, (step,))
    artifact_store = HostileArtifactStore(seed=1, drop_rate=1.0, corruption_rate=0.0)
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            artifact_store=artifact_store,
            execution_store=execution_store,
        ),
    )
    trace = result.trace
    assert any(
        event.event_type
        in {
            EventType.VERIFICATION_FAIL,
            EventType.STEP_FAILED,
            EventType.RETRIEVAL_FAILED,
        }
        for event in trace.events
    )
    assert trace.events[-1].event_type in {
        EventType.VERIFICATION_FAIL,
        EventType.STEP_FAILED,
        EventType.RETRIEVAL_FAILED,
    }
