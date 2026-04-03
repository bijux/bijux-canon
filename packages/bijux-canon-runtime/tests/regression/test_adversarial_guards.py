# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import bijux_agent
import bijux_rag
import bijux_rar
import bijux_vex
import pytest

from agentic_flows.core.authority import authority_token
from agentic_flows.runtime.artifact_store import InMemoryArtifactStore
from agentic_flows.runtime.budget import BudgetState
from agentic_flows.runtime.context import ExecutionContext, RunMode
from agentic_flows.runtime.observability.capture.trace_recorder import TraceRecorder
from agentic_flows.runtime.observability.classification.entropy import EntropyLedger
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    execute_flow,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    RunMode as FlowRunMode,
)
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.artifact.reasoning_claim import ReasoningClaim
from agentic_flows.spec.model.datasets.retrieval_request import RetrievalRequest
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.reasoning_step import ReasoningStep
from agentic_flows.spec.model.verification.arbitration_policy import ArbitrationPolicy
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.ontology import (
    ArbitrationRule,
    ArtifactScope,
    ArtifactType,
    DeterminismLevel,
    EntropyMagnitude,
    EvidenceDeterminism,
    FlowState,
    StepType,
    VerificationRandomness,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ArtifactID,
    BundleID,
    ClaimID,
    ContentHash,
    ContractID,
    EnvironmentFingerprint,
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
    EntropySource,
    EventType,
    ReplayAcceptability,
)
from tests.helpers import build_claim_statement

pytestmark = pytest.mark.regression


def test_fabricated_artifact_rejected() -> None:
    context = ExecutionContext(
        authority=authority_token(),
        seed="seed",
        environment_fingerprint=EnvironmentFingerprint("env"),
        parent_flow_id=None,
        child_flow_ids=(),
        tenant_id=TenantID("tenant-a"),
        artifact_store=InMemoryArtifactStore(),
        trace_recorder=TraceRecorder(),
        mode=RunMode.LIVE,
        verification_policy=VerificationPolicy(
            spec_version="v1",
            verification_level="baseline",
            failure_mode="halt",
            randomness_tolerance=VerificationRandomness.DETERMINISTIC,
            arbitration_policy=ArbitrationPolicy(
                spec_version="v1",
                rule=ArbitrationRule.UNANIMOUS,
                quorum_threshold=None,
            ),
            required_evidence=(),
            max_rule_cost=100,
            rules=(),
            fail_on=(),
            escalate_on=(),
        ),
        observers=(),
        budget=BudgetState(None),
        entropy=EntropyLedger(
            EntropyBudget(
                spec_version="v1",
                allowed_sources=(EntropySource.SEEDED_RNG,),
                max_magnitude=EntropyMagnitude.LOW,
            ),
            intents=(),
            allowed_variance_class=None,
        ),
        execution_store=None,
        run_id=None,
        resume_from_step_index=-1,
        starting_event_index=0,
        starting_evidence_index=0,
        starting_tool_invocation_index=0,
        starting_entropy_index=0,
        initial_claim_ids=(),
        initial_artifacts=[],
        initial_evidence=[],
        initial_tool_invocations=[],
        _step_evidence={},
        _step_artifacts={},
    )
    fabricated = Artifact(
        spec_version="v1",
        artifact_id=ArtifactID("fabricated"),
        tenant_id=TenantID("tenant-a"),
        artifact_type=ArtifactType.AGENT_INVOCATION,
        producer="agent",
        parent_artifacts=(),
        content_hash=ContentHash("hash"),
        scope=ArtifactScope.WORKING,
    )

    with pytest.raises(KeyError):
        context.record_artifacts(0, [fabricated])


def test_reused_artifact_id_rejected(
    baseline_policy,
    resolved_flow_factory,
    entropy_budget,
    replay_envelope,
    dataset_descriptor,
    execution_store,
) -> None:
    bijux_agent.run = lambda **_kwargs: [
        {
            "artifact_id": "dup-artifact",
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
                    supported_by=(evidence[0].evidence_id,),
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
            evidence_ids=(evidence[0].evidence_id,),
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
    step_one = ResolvedStep(
        spec_version="v1",
        step_index=0,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID("agent-a"),
        inputs_fingerprint=InputsFingerprint("inputs-a"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-a"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs-a"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=request,
    )
    step_two = ResolvedStep(
        spec_version="v1",
        step_index=1,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID("agent-b"),
        inputs_fingerprint=InputsFingerprint("inputs-b"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-b"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs-b"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=request,
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-reuse"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"), AgentID("agent-b")),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-1"),),
        verification_gates=(GateID("gate-a"),),
    )
    resolved_flow = resolved_flow_factory(manifest, (step_one, step_two))

    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=FlowRunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )

    assert any(
        event.event_type == EventType.STEP_FAILED for event in result.trace.events
    )
    assert result.trace.events[-1].event_type in {
        EventType.STEP_FAILED,
        EventType.VERIFICATION_ARBITRATION,
    }


def test_fake_evidence_id_rejected(
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
    bijux_rar.reason = lambda **_kwargs: ReasoningBundle(
        spec_version="v1",
        bundle_id=BundleID("bundle-1"),
        claims=(
            ReasoningClaim(
                spec_version="v1",
                claim_id=ClaimID("claim-1"),
                statement="ev-2",
                confidence=0.5,
                supported_by=(EvidenceID("ev-2"),),
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
        evidence_ids=(EvidenceID("ev-2"),),
        producer_agent_id=AgentID("agent-a"),
    )

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
        flow_id=FlowID("flow-fake-evidence"),
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

    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=FlowRunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )

    assert any(
        event.event_type == EventType.REASONING_FAILED for event in result.trace.events
    )
    assert result.trace.events[-1].event_type in {
        EventType.REASONING_FAILED,
        EventType.VERIFICATION_ARBITRATION,
    }
