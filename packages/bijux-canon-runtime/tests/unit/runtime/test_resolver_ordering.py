# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from bijux_canon_runtime.ontology.ids import AgentID, DatasetID, FlowID, TenantID
from bijux_canon_runtime.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)
import pytest

pytestmark = pytest.mark.unit


def test_resolver_uses_lexical_tiebreak_for_ordering() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-ordering"),
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
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID("bravo"), AgentID("alpha"), AgentID("charlie")),
        dependencies=(),
        retrieval_contracts=(),
        verification_gates=(),
    )

    resolved = ExecutionPlanner().resolve(manifest)
    step_agents = tuple(step.agent_id for step in resolved.plan.steps)
    assert step_agents == (AgentID("alpha"), AgentID("bravo"), AgentID("charlie"))


def test_resolver_rejects_duplicate_dependency_edges() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-ordering"),
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
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID("alpha"), AgentID("bravo")),
        dependencies=("bravo:alpha", "bravo:alpha"),
        retrieval_contracts=(),
        verification_gates=(),
    )

    with pytest.raises(
        ValueError, match="dependencies must not contain duplicate edges"
    ):
        ExecutionPlanner().resolve(manifest)


def test_resolver_normalizes_declared_dependency_order() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-ordering"),
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
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID("alpha"), AgentID("bravo"), AgentID("charlie")),
        dependencies=("charlie:bravo", "charlie:alpha"),
        retrieval_contracts=(),
        verification_gates=(),
    )

    resolved = ExecutionPlanner().resolve(manifest)
    charlie_step = next(
        step for step in resolved.plan.steps if step.agent_id == AgentID("charlie")
    )

    assert charlie_step.declared_dependencies == (AgentID("alpha"), AgentID("bravo"))
