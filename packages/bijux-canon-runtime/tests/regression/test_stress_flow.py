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

pytestmark = pytest.mark.regression


def test_plan_mode_handles_multiple_agents(
    entropy_budget, replay_envelope, dataset_descriptor
) -> None:
    agents = tuple(AgentID(f"agent-{index}") for index in range(5))
    dependencies = ("agent-1:agent-0", "agent-2:agent-1", "agent-3:agent-2")
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-stress"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=agents,
        dependencies=dependencies,
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )

    result = execute_flow(
        manifest,
        config=ExecutionConfig(
            mode=RunMode.PLAN, determinism_level=manifest.determinism_level
        ),
    )
    assert len(result.resolved_flow.plan.steps) == len(agents)
