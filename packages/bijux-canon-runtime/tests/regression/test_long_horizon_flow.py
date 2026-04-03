# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import bijux_agent
import bijux_rag
import bijux_rar
import bijux_vex
import pytest

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
    FlowID,
    GateID,
    InputsFingerprint,
    RequestID,
    StepID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import ReplayAcceptability

pytestmark = pytest.mark.regression


def test_long_horizon_flow_is_stable(
    baseline_policy,
    resolved_flow_factory,
    entropy_budget,
    replay_envelope,
    dataset_descriptor,
    execution_store,
) -> None:
    bijux_agent.run = lambda agent_id, **_kwargs: [
        {
            "artifact_id": f"artifact-{agent_id}",
            "artifact_type": "agent_invocation",
            "content": f"payload-{agent_id}",
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
            "vector_contract_id": "contract-a",
        }
    ]
    bijux_vex.enforce_contract = lambda *_args, **_kwargs: True

    def _reason(agent_outputs, evidence, seed):
        evidence_item = evidence[0]
        artifact_hash = agent_outputs[0].content_hash
        statement = (
            f"ok {evidence_item.evidence_id} {evidence_item.content_hash} "
            f"{artifact_hash}"
        )
        return ReasoningBundle(
            spec_version="v1",
            bundle_id=BundleID(f"bundle-{seed}"),
            claims=(
                ReasoningClaim(
                    spec_version="v1",
                    claim_id=ClaimID(f"claim-{seed}"),
                    statement=statement,
                    confidence=0.9,
                    supported_by=(evidence_item.evidence_id,),
                ),
            ),
            steps=(
                ReasoningStep(
                    spec_version="v1",
                    step_id=StepID(f"step-{seed}"),
                    input_claims=(),
                    output_claims=(ClaimID(f"claim-{seed}"),),
                    method="deduction",
                ),
            ),
            evidence_ids=(evidence_item.evidence_id,),
            producer_agent_id=AgentID("agent-0"),
        )

    bijux_rar.reason = _reason
    request = RetrievalRequest(
        spec_version="v1",
        request_id=RequestID("req-1"),
        query="test",
        vector_contract_id=ContractID("contract-a"),
        top_k=1,
        scope="project",
    )
    steps: list[ResolvedStep] = []
    dependencies: dict[str, list[str]] = {}
    for index in range(50):
        agent_id = AgentID(f"agent-{index}")
        deps = []
        if index > 0:
            deps = [f"agent-{index - 1}"]
        dependencies[str(agent_id)] = deps
        steps.append(
            ResolvedStep(
                spec_version="v1",
                step_index=index,
                step_type=StepType.AGENT,
                determinism_level=DeterminismLevel.STRICT,
                agent_id=agent_id,
                inputs_fingerprint=InputsFingerprint(f"inputs-{index}"),
                declared_dependencies=tuple(AgentID(dep) for dep in deps),
                expected_artifacts=(),
                agent_invocation=AgentInvocation(
                    spec_version="v1",
                    agent_id=agent_id,
                    agent_version=VersionID("0.0.0"),
                    inputs_fingerprint=InputsFingerprint(f"inputs-{index}"),
                    declared_outputs=(),
                    execution_mode="seeded",
                ),
                retrieval_request=request,
            )
        )

    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-long"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=tuple(step.agent_id for step in steps),
        dependencies=tuple(
            f"agent-{index}:agent-{index - 1}" for index in range(1, 50)
        ),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    resolved_flow = resolved_flow_factory(
        manifest, tuple(steps), dependencies=dependencies
    )

    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )
    assert result.trace.finalized is True
    assert len(result.trace.events) >= 50

    manifest_two = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-long-2"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=tuple(step.agent_id for step in steps),
        dependencies=tuple(
            f"agent-{index}:agent-{index - 1}" for index in range(1, 50)
        ),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    resolved_flow_two = resolved_flow_factory(
        manifest_two, tuple(steps), dependencies=dependencies
    )
    result_two = execute_flow(
        resolved_flow=resolved_flow_two,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )
    assert result_two.trace.finalized is True
    assert result.trace.plan_hash != result_two.trace.plan_hash
