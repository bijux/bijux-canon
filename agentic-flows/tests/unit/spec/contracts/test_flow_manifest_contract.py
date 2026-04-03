# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.contracts.flow_contract import validate
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


def test_invalid_manifest_rejected() -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID(""),
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
        agents=(AgentID("agent-a"),),
        dependencies=("dep-a",),
        retrieval_contracts=(ContractID("retrieval-a"),),
        verification_gates=(GateID("gate-a"),),
    )

    with pytest.raises(ValueError, match="flow_id must be a non-empty string"):
        validate(manifest)
