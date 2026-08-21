from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_runtime.application.execute_flow import ExecutionConfig, execute_flow
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.ontology.ids import ArtifactID, TenantID
from bijux_canon_runtime.runtime.persistence import (
    InMemoryArtifactPayloadStore,
    PayloadCollisionError,
)


_REQUIRED_PAYLOAD_SCHEMAS = (
    "source-derivative",
    "document",
    "chunk",
    "vector",
    "index-manifest",
    "evidence",
    "prompt",
    "response",
    "claim",
    "graph",
    "trace",
    "log",
    "report",
)


@pytest.mark.parametrize("payload_kind", _REQUIRED_PAYLOAD_SCHEMAS)
def test_store_retains_complete_payload_for_every_runtime_family(
    payload_kind: str,
) -> None:
    store = InMemoryArtifactPayloadStore()
    artifact = AddressedArtifact.from_json(
        {
            "kind": payload_kind,
            "payload": f"exact {payload_kind} content",
            "sequence": [0, 1, 2],
        },
        schema_id=f"bijux.runtime.{payload_kind}.v1",
        producer=f"bijux-canon-runtime:{payload_kind}",
    )

    store.put(artifact)
    loaded = store.load(artifact.descriptor.artifact_id)

    assert loaded == artifact
    assert loaded.canonical_bytes == artifact.canonical_bytes
    assert loaded.descriptor.size_bytes == len(artifact.canonical_bytes)


def test_payload_binding_resolves_exact_bytes_and_is_tenant_scoped() -> None:
    store = InMemoryArtifactPayloadStore()
    artifact = AddressedArtifact.from_bytes(
        b"retrieved ancient DNA evidence",
        schema_id="bijux.runtime.evidence.v1",
        media_type="text/plain",
        producer="bijux-canon-index:retrieval",
    )
    logical_id = ArtifactID("evidence-7-source-12")
    tenant = TenantID("tenant-a")

    store.put(artifact)
    binding = store.bind(
        tenant_id=tenant,
        logical_artifact_id=logical_id,
        target_artifact_id=artifact.descriptor.artifact_id,
    )

    assert binding.logical_artifact_id != binding.target_artifact_id
    assert store.resolve(logical_id, tenant_id=tenant) == artifact
    with pytest.raises(KeyError, match="binding not found"):
        store.resolve(logical_id, tenant_id=TenantID("tenant-b"))


def test_payload_writes_are_idempotent_and_conflicts_fail_closed() -> None:
    store = InMemoryArtifactPayloadStore()
    artifact = AddressedArtifact.from_json(
        {"claim": "migration changed ancestry"},
        schema_id="bijux.runtime.claim.v1",
        producer="bijux-canon-reason:claim",
    )
    store.put(artifact)
    store.put(artifact)

    conflicting = replace(
        artifact,
        descriptor=replace(
            artifact.descriptor,
            producer="bijux-canon-agent:unsupported-conflict",
        ),
    )
    with pytest.raises(PayloadCollisionError, match="conflicting"):
        store.put(conflicting)

    store.bind(
        tenant_id=TenantID("tenant-a"),
        logical_artifact_id=ArtifactID("claim-current"),
        target_artifact_id=artifact.descriptor.artifact_id,
    )
    replacement = AddressedArtifact.from_json(
        {"claim": "different payload"},
        schema_id="bijux.runtime.claim.v1",
        producer="bijux-canon-reason:claim",
    )
    store.put(replacement)
    with pytest.raises(PayloadCollisionError, match="already bound"):
        store.bind(
            tenant_id=TenantID("tenant-a"),
            logical_artifact_id=ArtifactID("claim-current"),
            target_artifact_id=replacement.descriptor.artifact_id,
        )


def test_runtime_execution_persists_complete_executor_payloads(
    resolved_flow,
    baseline_policy,
    execution_store,
) -> None:
    store = InMemoryArtifactPayloadStore()
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            verification_policy=baseline_policy,
            payload_store=store,
            execution_store=execution_store,
        ),
    )

    assert result.artifacts
    for artifact in result.artifacts:
        payload = store.resolve(
            artifact.artifact_id,
            tenant_id=resolved_flow.manifest.tenant_id,
        )
        assert payload.canonical_bytes
        assert payload.descriptor.schema_id == "bijux.runtime.executor-state.v1"
