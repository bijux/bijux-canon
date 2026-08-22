from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    AtomicFilesystemArtifactPayloadStore,
    EvidenceBundleExporter,
    EvidenceBundleIntegrityError,
    EvidenceBundleLimits,
    EvidenceRedactionPolicy,
    PublicationItem,
    RuntimeArtifactInspector,
)
from bijux_canon_runtime.runtime.pagination import PageRequest


def _workspace(tmp_path: Path, resolved_flow):
    database = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(database)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    payload_store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    source = AddressedArtifact.from_json(
        {"text": "steppe ancestry expanded westward"},
        schema_id="bijux.ingest.source.v1",
        producer="bijux-canon-ingest:source",
    )
    restricted = AddressedArtifact.from_json(
        {"reviewer_note": "restricted participant metadata"},
        schema_id="bijux.runtime.restricted-note.v1",
        producer="bijux-canon-runtime:review",
    )
    answer = AddressedArtifact.from_json(
        {"claim": "migration materially changed ancestry"},
        schema_id="bijux.reason.answer.v1",
        producer="bijux-canon-reason:answer",
        dependencies=(
            source.descriptor.artifact_id,
            restricted.descriptor.artifact_id,
        ),
    )
    coordinator = ArtifactPublicationCoordinator(
        payload_store=payload_store,
        database_path=database,
    )
    coordinator.publish(
        tenant_id=resolved_flow.manifest.tenant_id,
        run_id=run_id,
        transaction_id="publish-evidence",
        items=(
            PublicationItem("source/current", 0, source),
            PublicationItem("review-note/current", 0, restricted),
            PublicationItem("answer/current", 0, answer),
        ),
        created_at="2026-08-22T00:00:00+00:00",
        completed_at="2026-08-22T00:00:01+00:00",
    )
    return database, payload_store, run_id, source, restricted, answer


def test_inspector_lists_resolves_and_verifies_without_storage_paths(
    tmp_path: Path,
    resolved_flow,
) -> None:
    database, payload_store, run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    inspector = RuntimeArtifactInspector(
        database_path=database,
        payload_store=payload_store,
    )

    records = inspector.list_artifacts()
    resolution = inspector.resolve(
        tenant_id=resolved_flow.manifest.tenant_id,
        run_id=run_id,
        logical_artifact_id="answer/current",
    )

    assert len(records) == 3
    assert all(record.integrity_status == "valid" for record in records)
    assert all("reachable" in record.classifications for record in records)
    assert resolution.reference.revision == 0
    assert resolution.target.artifact_id == answer.descriptor.artifact_id
    assert resolution.target.valid
    assert str(tmp_path) not in repr(records)
    missing = inspector.verify(ArtifactID("sha256:" + "f" * 64))
    assert not missing.valid
    assert missing.failure == "KeyError"


def test_artifact_inventory_uses_snapshot_bound_cursor_pages(
    tmp_path: Path,
    resolved_flow,
) -> None:
    database, payload_store, _run_id, *_ = _workspace(tmp_path, resolved_flow)
    inspector = RuntimeArtifactInspector(
        database_path=database,
        payload_store=payload_store,
    )

    first = inspector.list_artifacts_page(PageRequest(limit=2))
    cursor = first.page["next_cursor"]
    assert len(first.artifacts) == 2
    assert isinstance(cursor, str)

    second = inspector.list_artifacts_page(PageRequest(limit=2, cursor=cursor))
    assert len(second.artifacts) == 1
    assert second.page["offset"] == 2
    assert second.page["next_cursor"] is None
    assert first.page["snapshot_sha256"] == second.page["snapshot_sha256"]
    assert {item.artifact_id for item in (*first.artifacts, *second.artifacts)} == set(
        payload_store.artifact_ids()
    )

    with pytest.raises(ValueError, match="cursor is invalid"):
        inspector.list_artifacts_page(PageRequest(limit=2, cursor=cursor + "x"))


def test_export_is_deterministic_dependency_complete_and_policy_redacted(
    tmp_path: Path,
    resolved_flow,
) -> None:
    _database, payload_store, _run_id, source, restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    exporter = EvidenceBundleExporter(payload_store)
    policy = EvidenceRedactionPolicy(
        policy_id="omit-restricted-review-notes",
        redact_schema_ids=("bijux.runtime.restricted-note.v1",),
    )

    first = exporter.export(
        root_artifact_ids=(answer.descriptor.artifact_id,),
        destination=tmp_path / "bundle-a",
        redaction_policy=policy,
    )
    second = exporter.export(
        root_artifact_ids=(answer.descriptor.artifact_id,),
        destination=tmp_path / "bundle-b",
        redaction_policy=policy,
    )
    verified = exporter.verify_export(tmp_path / "bundle-a")

    assert first.bundle_sha256 == second.bundle_sha256
    assert (tmp_path / "bundle-a" / "manifest.json").read_bytes() == (
        tmp_path / "bundle-b" / "manifest.json"
    ).read_bytes()
    assert first.artifact_ids == tuple(
        sorted(
            (
                source.descriptor.artifact_id,
                restricted.descriptor.artifact_id,
                answer.descriptor.artifact_id,
            )
        )
    )
    assert first.redacted_artifact_ids == (restricted.descriptor.artifact_id,)
    assert verified.valid
    assert verified.artifact_count == 3
    assert verified.included_payload_count == 2
    assert verified.redacted_payload_count == 1
    assert not verified.complete_payloads
    manifest_text = (tmp_path / "bundle-a" / "manifest.json").read_text(
        encoding="utf-8"
    )
    assert str(tmp_path) not in manifest_text
    manifest = json.loads(manifest_text)
    restricted_entry = next(
        item
        for item in manifest["artifacts"]
        if item["artifact_id"] == str(restricted.descriptor.artifact_id)
    )
    assert restricted_entry["payload_disposition"] == "redacted"
    assert restricted_entry["payload_file"] is None


def test_export_verification_fails_closed_on_payload_tampering(
    tmp_path: Path,
    resolved_flow,
) -> None:
    _database, payload_store, _run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    bundle = tmp_path / "bundle"
    EvidenceBundleExporter(payload_store).export(
        root_artifact_ids=(answer.descriptor.artifact_id,),
        destination=bundle,
        redaction_policy=EvidenceRedactionPolicy(policy_id="include-all"),
    )
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    answer_entry = next(
        item
        for item in manifest["artifacts"]
        if item["artifact_id"] == str(answer.descriptor.artifact_id)
    )
    (bundle / answer_entry["payload_file"]).write_bytes(b"tampered")

    with pytest.raises(EvidenceBundleIntegrityError, match="verification failed"):
        EvidenceBundleExporter.verify_export(bundle)


def test_export_requires_new_destination(tmp_path: Path, resolved_flow) -> None:
    _database, payload_store, _run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        EvidenceBundleExporter(payload_store).export(
            root_artifact_ids=(answer.descriptor.artifact_id,),
            destination=destination,
            redaction_policy=EvidenceRedactionPolicy(policy_id="include-all"),
        )


@pytest.mark.parametrize(
    "limits",
    [
        EvidenceBundleLimits(max_artifacts=2),
        EvidenceBundleLimits(max_bundle_bytes=1),
        EvidenceBundleLimits(max_artifact_bytes=1),
    ],
)
def test_export_fails_before_publication_when_a_hard_limit_is_exceeded(
    tmp_path: Path,
    resolved_flow,
    limits: EvidenceBundleLimits,
) -> None:
    _database, payload_store, _run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    destination = tmp_path / "bounded-bundle"

    with pytest.raises(ValueError, match="exceed"):
        EvidenceBundleExporter(payload_store, limits=limits).export(
            root_artifact_ids=(answer.descriptor.artifact_id,),
            destination=destination,
            redaction_policy=EvidenceRedactionPolicy(policy_id="include-all"),
        )

    assert not destination.exists()


def test_export_streams_payloads_without_materializing_store_objects(
    tmp_path: Path,
    resolved_flow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _database, payload_store, _run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )

    def reject_load(_artifact_id: ArtifactID):
        raise AssertionError("streamed export must not call load")

    monkeypatch.setattr(payload_store, "load", reject_load)
    manifest = EvidenceBundleExporter(
        payload_store,
        limits=EvidenceBundleLimits(stream_chunk_bytes=7),
    ).export(
        root_artifact_ids=(answer.descriptor.artifact_id,),
        destination=tmp_path / "streamed-bundle",
        redaction_policy=EvidenceRedactionPolicy(policy_id="include-all"),
    )

    assert len(manifest.artifact_ids) == 3


def test_export_verification_rejects_mutable_absolute_paths(
    tmp_path: Path,
    resolved_flow,
) -> None:
    _database, payload_store, _run_id, _source, _restricted, answer = _workspace(
        tmp_path, resolved_flow
    )
    bundle = tmp_path / "bundle"
    EvidenceBundleExporter(payload_store).export(
        root_artifact_ids=(answer.descriptor.artifact_id,),
        destination=bundle,
        redaction_policy=EvidenceRedactionPolicy(policy_id="include-all"),
    )
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["descriptor_file"] = str(tmp_path / "mutable.json")
    unsigned = {
        key: value for key, value in manifest.items() if key != "bundle_sha256"
    }
    manifest["bundle_sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(EvidenceBundleIntegrityError, match="verification failed"):
        EvidenceBundleExporter.verify_export(bundle)
