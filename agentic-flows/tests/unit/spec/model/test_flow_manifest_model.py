# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    FlowID,
    GateID,
    TenantID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)

pytestmark = pytest.mark.unit


def test_flow_manifest_model_allows_invalid_state() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID(""),
        tenant_id=TenantID(""),
        flow_state=FlowState.DRAFT,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
            max_magnitude=EntropyMagnitude.LOW,
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=0.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID(""),
            tenant_id=TenantID(""),
            dataset_version="",
            dataset_hash="",
            dataset_state=DatasetState.EXPERIMENTAL,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        agents=(AgentID(""),),
        dependencies=("invalid",),
        retrieval_contracts=(ContractID(""),),
        verification_gates=(GateID(""),),
    )

    assert manifest.flow_id == ""
