# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from bijux_canon_runtime.contracts.flow_contract import validate
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
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    FlowID,
    GateID,
    TenantID,
)
from bijux_canon_runtime.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)
import pytest

pytestmark = pytest.mark.unit


def _base_manifest(*, dependencies: tuple[str, ...]) -> FlowManifest:
    return FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-a"),
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
            storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"), AgentID("agent-b")),
        dependencies=dependencies,
        retrieval_contracts=(ContractID("retrieval-a"),),
        verification_gates=(GateID("gate-a"),),
    )


def test_invalid_manifest_rejected() -> None:
    manifest = _base_manifest(dependencies=("dep-a",))
    manifest = FlowManifest(
        **{**manifest.__dict__, "flow_id": FlowID(""), "agents": (AgentID("agent-a"),)}
    )

    with pytest.raises(ValueError, match="flow_id must be a non-empty string"):
        validate(manifest)


def test_manifest_rejects_duplicate_dependency_edges() -> None:
    manifest = _base_manifest(
        dependencies=("agent-b:agent-a", "agent-b:agent-a"),
    )

    with pytest.raises(
        ValueError, match="dependencies must not contain duplicate edges"
    ):
        validate(manifest)


def test_manifest_rejects_self_referential_dependency() -> None:
    manifest = _base_manifest(dependencies=("agent-a:agent-a",))

    with pytest.raises(
        ValueError, match="dependencies must not reference the same agent"
    ):
        validate(manifest)
