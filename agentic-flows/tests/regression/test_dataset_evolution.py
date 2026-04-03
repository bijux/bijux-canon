# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.runtime.orchestration.replay_store import replay_with_store
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.ontology import (
    DatasetState,
    DeterminismLevel,
    FlowState,
    StepType,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    DatasetID,
    FlowID,
    InputsFingerprint,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import ReplayAcceptability

pytestmark = pytest.mark.regression


def test_dataset_evolution_blocks_replay(
    entropy_budget,
    replay_envelope,
    resolved_flow_factory,
    execution_store,
    execution_read_store,
) -> None:
    dataset_v1 = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("evolution-set"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="48ac7966795722d2d0802c39f8c0c012",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/evolution_v1.jsonl",
    )
    dataset_v2 = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("evolution-set"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="2.0.0",
        dataset_hash="f6b9e312c56b0231a5e6ad414e089fde",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/evolution_v2.jsonl",
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
        retrieval_request=None,
    )
    manifest_v1 = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-evolution"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_v1,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(),
        verification_gates=(),
    )
    manifest_v2 = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-evolution"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_v2,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(),
        verification_gates=(),
    )
    flow_v1 = resolved_flow_factory(manifest_v1, (step,))
    flow_v2 = resolved_flow_factory(manifest_v2, (step,))

    run = execute_flow(
        resolved_flow=flow_v1,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=manifest_v1.determinism_level,
            execution_store=execution_store,
        ),
    )

    with pytest.raises(ValueError, match="dataset"):
        replay_with_store(
            store=execution_read_store,
            run_id=run.run_id,
            tenant_id=run.trace.tenant_id,
            resolved_flow=flow_v2,
            config=ExecutionConfig(
                mode=RunMode.DRY_RUN,
                determinism_level=manifest_v2.determinism_level,
                execution_store=execution_store,
            ),
        )
