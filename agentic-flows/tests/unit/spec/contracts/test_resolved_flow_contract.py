# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.contracts.execution_plan_contract import (
    validate as validate_execution_plan,
)
from agentic_flows.spec.contracts.flow_contract import (
    validate as validate_flow_manifest,
)
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
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
    PlanHash,
    ResolverID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)

pytestmark = pytest.mark.unit


def _manifest(*, dependencies: tuple[str, ...]) -> FlowManifest:
    return FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-resolved"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
            max_magnitude=EntropyMagnitude.LOW,
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=0.9,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"), AgentID("agent-b")),
        dependencies=dependencies,
        retrieval_contracts=(),
        verification_gates=(),
    )


def _resolved_step(
    *,
    agent_id: AgentID,
    step_index: int,
    declared_dependencies: tuple[AgentID, ...],
    entropy_budget: EntropyBudget | None = None,
) -> ResolvedStep:
    inputs_fingerprint = InputsFingerprint(f"inputs-{agent_id}")
    return ResolvedStep(
        spec_version="v1",
        step_index=step_index,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
        agent_id=agent_id,
        inputs_fingerprint=inputs_fingerprint,
        declared_dependencies=declared_dependencies,
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=agent_id,
            agent_version=VersionID("v1"),
            inputs_fingerprint=inputs_fingerprint,
            declared_outputs=(),
            execution_mode="default",
        ),
        retrieval_request=None,
        declared_entropy_budget=entropy_budget,
    )


def test_manifest_rejects_dependency_cycle() -> None:
    manifest = _manifest(
        dependencies=("agent-a:agent-b", "agent-b:agent-a"),
    )

    with pytest.raises(ValueError, match="dependencies must form a reachable DAG"):
        validate_flow_manifest(manifest)


def test_execution_plan_rejects_inverted_dependencies() -> None:
    manifest = _manifest(dependencies=("agent-a:agent-b",))
    plan = ExecutionSteps(
        spec_version="v1",
        flow_id=manifest.flow_id,
        tenant_id=manifest.tenant_id,
        flow_state=manifest.flow_state,
        determinism_level=manifest.determinism_level,
        replay_mode=manifest.replay_mode,
        replay_acceptability=manifest.replay_acceptability,
        entropy_budget=manifest.entropy_budget,
        allowed_variance_class=manifest.allowed_variance_class,
        nondeterminism_intent=manifest.nondeterminism_intent,
        replay_envelope=manifest.replay_envelope,
        dataset=manifest.dataset,
        allow_deprecated_datasets=manifest.allow_deprecated_datasets,
        steps=(
            _resolved_step(
                agent_id=AgentID("agent-b"),
                step_index=0,
                declared_dependencies=(AgentID("agent-a"),),
                entropy_budget=manifest.entropy_budget,
            ),
            _resolved_step(
                agent_id=AgentID("agent-a"),
                step_index=1,
                declared_dependencies=(),
                entropy_budget=manifest.entropy_budget,
            ),
        ),
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
    )

    with pytest.raises(ValueError, match="dependencies must precede dependent steps"):
        validate_execution_plan(
            ExecutionPlan(spec_version="v1", manifest=manifest, plan=plan)
        )
