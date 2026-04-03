# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import bijux_agent
import pytest

from agentic_flows.core.errors import NonDeterminismViolationError
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.datasets.retrieval_request import RetrievalRequest
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    EntropyMagnitude,
    EvidenceDeterminism,
    FlowState,
    StepType,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContentHash,
    ContractID,
    EvidenceID,
    FlowID,
    InputsFingerprint,
    RequestID,
    StepID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    NonDeterminismIntentSource,
    ReplayAcceptability,
)


@pytest.mark.unit
def test_strict_determinism_aborts_on_first_entropy_violation(
    baseline_policy,
    resolved_flow_factory,
    entropy_budget,
    replay_envelope,
    dataset_descriptor,
    execution_store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    step_one = ResolvedStep(
        spec_version="v1",
        step_index=0,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID("agent-a"),
        inputs_fingerprint=InputsFingerprint("inputs-0"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-a"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs-0"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=RetrievalRequest(
            spec_version="v1",
            request_id=RequestID("req-entropy"),
            query="entropy test",
            vector_contract_id=ContractID("contract-a"),
            top_k=1,
            scope="tests",
        ),
    )
    step_two = ResolvedStep(
        spec_version="v1",
        step_index=1,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID("agent-b"),
        inputs_fingerprint=InputsFingerprint("inputs-1"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-b"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs-1"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=None,
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-entropy"),
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
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(),
        nondeterminism_intent=(
            NonDeterministicIntent(
                spec_version="v1",
                source=NonDeterminismIntentSource.RETRIEVAL,
                min_entropy_magnitude=EntropyMagnitude.LOW,
                max_entropy_magnitude=EntropyMagnitude.LOW,
                justification="retrieval variance permitted for test",
            ),
        ),
    )
    resolved_flow = resolved_flow_factory(manifest, (step_one, step_two))

    retrieval_calls: list[int] = []
    agent_calls: list[str] = []

    def _retrieval_execute(_self, _step, context):
        retrieval_calls.append(_step.step_index)
        context.record_entropy(
            source=EntropySource.DATA,
            magnitude=EntropyMagnitude.LOW,
            description="unauthorized entropy",
            step_index=_step.step_index,
            nondeterminism_source=NonDeterminismSource(
                source=EntropySource.DATA,
                authorized=False,
                scope=StepID(str(_step.step_index)),
            ),
        )
        return [
            RetrievedEvidence(
                spec_version="v1",
                evidence_id=EvidenceID("ev-unauthorized"),
                tenant_id=TenantID("tenant-a"),
                determinism=EvidenceDeterminism.DETERMINISTIC,
                source_uri="file://datasets/retrieval_corpus.jsonl",
                content_hash=ContentHash("hash"),
                score=1.0,
                vector_contract_id=ContractID("contract-a"),
            )
        ]

    def _agent_run(**_kwargs):
        agent_calls.append(_kwargs["agent_id"])
        return [
            {
                "artifact_id": f"artifact-{_kwargs['agent_id']}",
                "artifact_type": "agent_invocation",
                "content": "payload",
                "parent_artifacts": [],
            }
        ]

    monkeypatch.setattr(
        "agentic_flows.runtime.execution.retrieval_executor.RetrievalExecutor.execute",
        _retrieval_execute,
    )
    bijux_agent.run = _agent_run

    with pytest.raises(NonDeterminismViolationError, match="explicit authorization"):
        execute_flow(
            resolved_flow=resolved_flow,
            config=ExecutionConfig(
                mode=RunMode.LIVE,
                determinism_level=manifest.determinism_level,
                verification_policy=baseline_policy,
                execution_store=execution_store,
                strict_determinism=True,
            ),
        )

    assert retrieval_calls == [0]
    assert agent_calls == []
