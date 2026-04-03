# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

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


def _normalize_for_json(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_for_json(item) for key, item in value.items()}
    return value


def test_golden_execution_plan(
    deterministic_environment, entropy_budget, replay_envelope, dataset_descriptor
) -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-golden"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("alpha"), AgentID("bravo"), AgentID("charlie")),
        dependencies=("bravo:alpha", "charlie:alpha"),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    result = execute_flow(
        manifest,
        config=ExecutionConfig(
            mode=RunMode.PLAN, determinism_level=manifest.determinism_level
        ),
    )
    payload = _normalize_for_json(asdict(result.resolved_flow.plan))
    golden_path = Path(__file__).parents[1] / "golden" / "test_execution_plan.json"
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert payload == expected
