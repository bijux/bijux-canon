# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.artifact_store import InMemoryArtifactStore
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
)
from agentic_flows.spec.ontology.ids import ArtifactID, ContentHash, TenantID

pytestmark = pytest.mark.unit


def test_artifact_store_creates_and_saves_artifact() -> None:
    store = InMemoryArtifactStore()
    artifact = store.create(
        spec_version="v1",
        artifact_id=ArtifactID("artifact-1"),
        tenant_id=TenantID("tenant-a"),
        artifact_type=ArtifactType.AGENT_INVOCATION,
        producer="agent",
        parent_artifacts=(),
        content_hash=ContentHash("hash"),
        scope=ArtifactScope.WORKING,
    )

    loaded = store.load(artifact.artifact_id, tenant_id=TenantID("tenant-a"))
    assert loaded == artifact


def test_artifact_ids_are_unique() -> None:
    store = InMemoryArtifactStore()
    store.create(
        spec_version="v1",
        artifact_id=ArtifactID("artifact-audit"),
        tenant_id=TenantID("tenant-a"),
        artifact_type=ArtifactType.REASONING_BUNDLE,
        producer="reasoning",
        parent_artifacts=(),
        content_hash=ContentHash("hash"),
        scope=ArtifactScope.AUDIT,
    )

    with pytest.raises(ValueError, match="Artifact IDs must be unique per run"):
        store.create(
            spec_version="v1",
            artifact_id=ArtifactID("artifact-audit"),
            tenant_id=TenantID("tenant-a"),
            artifact_type=ArtifactType.REASONING_BUNDLE,
            producer="reasoning",
            parent_artifacts=(),
            content_hash=ContentHash("hash-2"),
            scope=ArtifactScope.WORKING,
        )
