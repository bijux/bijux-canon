from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.ontology.ids import ArtifactID, TenantID
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
    PayloadCollisionError,
)


def test_atomic_payload_survives_restart_with_exact_bytes(tmp_path: Path) -> None:
    artifact = AddressedArtifact.from_bytes(
        b"exact admitted JATS payload\x00with binary-safe bytes",
        schema_id="bijux.ingest.source-derivative.v1",
        media_type="application/xml",
        producer="bijux-canon-ingest:jats",
    )
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    store.put(artifact)

    restarted = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    loaded = restarted.load(artifact.descriptor.artifact_id)

    assert loaded == artifact
    assert loaded.canonical_bytes == artifact.canonical_bytes


def test_identical_payload_publication_is_idempotent(tmp_path: Path) -> None:
    artifact = AddressedArtifact.from_json(
        {"index": "ancient-dna", "dimensions": 384},
        schema_id="bijux.index.manifest.v1",
        producer="bijux-canon-index:build",
    )
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    store.put(artifact)
    digest = str(artifact.descriptor.artifact_id).removeprefix("sha256:")
    payload_path = (
        tmp_path / "cas" / "objects" / "sha256" / digest[:2] / digest / "payload"
    )
    first_stat = payload_path.stat()

    store.put(artifact)

    second_stat = payload_path.stat()
    assert second_stat.st_ino == first_stat.st_ino
    assert second_stat.st_mtime_ns == first_stat.st_mtime_ns


def test_corrupt_existing_payload_fails_closed_without_replacement(
    tmp_path: Path,
) -> None:
    artifact = AddressedArtifact.from_bytes(
        b"original vector bytes",
        schema_id="bijux.index.vector.v1",
        media_type="application/octet-stream",
        producer="bijux-canon-index:embedding",
    )
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    store.put(artifact)
    digest = str(artifact.descriptor.artifact_id).removeprefix("sha256:")
    payload_path = (
        tmp_path / "cas" / "objects" / "sha256" / digest[:2] / digest / "payload"
    )
    payload_path.write_bytes(b"corrupt vector bytes")

    with pytest.raises(PayloadCollisionError, match="corrupt durable content"):
        store.put(artifact)

    assert payload_path.read_bytes() == b"corrupt vector bytes"


def test_abandoned_partial_writes_are_cleaned_on_restart(tmp_path: Path) -> None:
    root = tmp_path / "cas"
    abandoned_directory = root / "staging" / "deadbeef.partial"
    abandoned_directory.mkdir(parents=True)
    (abandoned_directory / "payload").write_bytes(b"never published")
    abandoned_file = root / "staging" / "orphan.partial"
    abandoned_file.write_bytes(b"never published")
    unrelated = root / "staging" / "retain.audit"
    unrelated.write_text("retained", encoding="utf-8")

    AtomicFilesystemArtifactPayloadStore(root)

    assert not abandoned_directory.exists()
    assert not abandoned_file.exists()
    assert unrelated.read_text(encoding="utf-8") == "retained"


def test_descriptor_tampering_is_detected_after_restart(tmp_path: Path) -> None:
    artifact = AddressedArtifact.from_json(
        {"evidence": "exact text"},
        schema_id="bijux.runtime.evidence.v1",
        producer="bijux-canon-index:retrieval",
    )
    root = tmp_path / "cas"
    store = AtomicFilesystemArtifactPayloadStore(root)
    store.put(artifact)
    digest = str(artifact.descriptor.artifact_id).removeprefix("sha256:")
    descriptor_path = (
        root / "objects" / "sha256" / digest[:2] / digest / "descriptor.json"
    )
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    descriptor["producer"] = "tampered-producer"
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")

    with pytest.raises(ValueError, match="failed validation"):
        AtomicFilesystemArtifactPayloadStore(root).load(artifact.descriptor.artifact_id)


def test_binding_requires_a_durable_target(tmp_path: Path) -> None:
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    with pytest.raises(KeyError, match="payload not found"):
        store.bind(
            tenant_id=TenantID("tenant-a"),
            logical_artifact_id=ArtifactID("logical-artifact"),
            target_artifact_id=ArtifactID("sha256:" + "a" * 64),
        )
