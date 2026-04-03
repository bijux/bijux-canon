# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    FlowID,
    GateID,
    TenantID,
)
from agentic_flows.spec.ontology.public import ReplayAcceptability

pytestmark = pytest.mark.e2e


def test_execution_plan_orders_dependencies(
    entropy_budget, replay_envelope, dataset_descriptor
) -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-order"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"), AgentID("agent-b"), AgentID("agent-c")),
        dependencies=("agent-b:agent-a", "agent-c:agent-b"),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )

    result = execute_flow(
        manifest,
        config=ExecutionConfig(
            mode=RunMode.PLAN, determinism_level=manifest.determinism_level
        ),
    )
    ordered = [step.agent_id for step in result.resolved_flow.plan.steps]
    assert ordered == [AgentID("agent-a"), AgentID("agent-b"), AgentID("agent-c")]
