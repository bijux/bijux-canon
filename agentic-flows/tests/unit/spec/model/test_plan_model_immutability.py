# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import dataclasses

import pytest

from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
    StepType,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    InputsFingerprint,
    ResolverID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)

pytestmark = pytest.mark.unit


def _make_step(index: int) -> ResolvedStep:
    return ResolvedStep(
        spec_version="v1",
        step_index=index,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=AgentID(f"agent-{index}"),
        inputs_fingerprint=InputsFingerprint(f"inputs-{index}"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID(f"agent-{index}"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint(f"inputs-{index}"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=None,
    )


def test_plan_is_structurally_immutable(plan_hash_for) -> None:
    step = _make_step(0)
    entropy_budget = EntropyBudget(
        spec_version="v1",
        allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
        max_magnitude=EntropyMagnitude.LOW,
    )
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("test-dataset"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="dataset-hash",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )
    replay_envelope = ReplayEnvelope(
        spec_version="v1",
        min_claim_overlap=1.0,
        max_contradiction_delta=0,
    )
    plan = ExecutionSteps(
        spec_version="v1",
        flow_id=FlowID("flow-immutable"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset,
        allow_deprecated_datasets=False,
        steps=(step,),
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=plan_hash_for(
            "flow-immutable",
            "tenant-a",
            FlowState.VALIDATED,
            (step,),
            {},
            determinism_level=DeterminismLevel.STRICT,
            replay_acceptability=ReplayAcceptability.EXACT_MATCH,
            entropy_budget=entropy_budget,
            replay_envelope=replay_envelope,
            dataset=dataset,
            allow_deprecated_datasets=False,
        ),
        resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
    )

    assert isinstance(plan.steps, tuple)
    assert isinstance(plan.steps[0].declared_dependencies, tuple)

    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.steps = ()

    with pytest.raises(AttributeError):
        plan.steps.append(step)

    with pytest.raises(AttributeError):
        plan.steps[0].declared_dependencies.append(AgentID("agent-x"))
