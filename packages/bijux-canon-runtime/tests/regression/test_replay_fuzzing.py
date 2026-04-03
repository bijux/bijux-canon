# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.determinism_guard import (
    semantic_artifact_fingerprint,
    semantic_evidence_fingerprint,
)
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
    EvidenceDeterminism,
)
from agentic_flows.spec.ontology.ids import (
    ArtifactID,
    ContentHash,
    ContractID,
    EvidenceID,
    TenantID,
)

pytestmark = pytest.mark.regression


def test_semantic_fingerprints_ignore_order() -> None:
    artifacts = [
        Artifact(
            spec_version="v1",
            artifact_id=ArtifactID("a"),
            tenant_id=TenantID("tenant-a"),
            artifact_type=ArtifactType.AGENT_INVOCATION,
            producer="agent",
            parent_artifacts=(),
            content_hash=ContentHash("hash-a"),
            scope=ArtifactScope.WORKING,
        ),
        Artifact(
            spec_version="v1",
            artifact_id=ArtifactID("b"),
            tenant_id=TenantID("tenant-a"),
            artifact_type=ArtifactType.AGENT_INVOCATION,
            producer="agent",
            parent_artifacts=(),
            content_hash=ContentHash("hash-b"),
            scope=ArtifactScope.WORKING,
        ),
    ]
    evidence = [
        RetrievedEvidence(
            spec_version="v1",
            evidence_id=EvidenceID("ev-1"),
            tenant_id=TenantID("tenant-a"),
            determinism=EvidenceDeterminism.DETERMINISTIC,
            source_uri="file://doc",
            content_hash=ContentHash("hash-ev-1"),
            score=0.9,
            vector_contract_id=ContractID("contract-a"),
        ),
        RetrievedEvidence(
            spec_version="v1",
            evidence_id=EvidenceID("ev-2"),
            tenant_id=TenantID("tenant-a"),
            determinism=EvidenceDeterminism.DETERMINISTIC,
            source_uri="file://doc",
            content_hash=ContentHash("hash-ev-2"),
            score=0.8,
            vector_contract_id=ContractID("contract-a"),
        ),
    ]

    assert semantic_artifact_fingerprint(artifacts) == semantic_artifact_fingerprint(
        list(reversed(artifacts))
    )
    assert semantic_evidence_fingerprint(evidence) == semantic_evidence_fingerprint(
        list(reversed(evidence))
    )
