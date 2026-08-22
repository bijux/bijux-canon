from __future__ import annotations

from pathlib import Path

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.runtime.persistence import (
    ArtifactPublicationCoordinator,
    AtomicFilesystemArtifactPayloadStore,
    BackupIntegrityError,
    PublicationItem,
    RuntimeBackupManager,
)


def test_backup_restore_copies_only_reachable_payloads_and_verifies_identity(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(db_path)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    first = AddressedArtifact.from_json(
        {"source": "ancient DNA"},
        schema_id="bijux.runtime.source.v1",
        producer="bijux-canon-ingest:source",
    )
    second = AddressedArtifact.from_json(
        {"answer": "migration"},
        schema_id="bijux.runtime.answer.v1",
        producer="bijux-canon-reason:answer",
        dependencies=(first.descriptor.artifact_id,),
    )
    coordinator = ArtifactPublicationCoordinator(
        payload_store=store,
        database_path=db_path,
    )
    coordinator.publish(
        tenant_id=resolved_flow.manifest.tenant_id,
        run_id=run_id,
        transaction_id="publish",
        items=(
            PublicationItem("source/current", 0, first),
            PublicationItem("answer/current", 0, second),
        ),
        created_at="2026-08-22T00:00:00+00:00",
        completed_at="2026-08-22T00:00:01+00:00",
    )
    orphan = AddressedArtifact.from_json(
        {"orphan": True},
        schema_id="bijux.runtime.orphan.v1",
        producer="bijux-canon-runtime:test",
    )
    store.put(orphan)
    manager = RuntimeBackupManager(database_path=db_path, payload_store=store)

    generation, manifest = manager.create_backup(
        backup_id="backup-a",
        destination_root=tmp_path / "backups",
        created_at="2026-08-22T00:00:02+00:00",
    )

    assert manifest.artifact_ids == tuple(
        sorted((first.descriptor.artifact_id, second.descriptor.artifact_id))
    )
    backup_store = AtomicFilesystemArtifactPayloadStore(generation / "cas")
    assert backup_store.load(first.descriptor.artifact_id) == first
    assert backup_store.load(second.descriptor.artifact_id) == second
    with pytest.raises(KeyError):
        backup_store.load(orphan.descriptor.artifact_id)

    result = RuntimeBackupManager.restore(
        backup_generation=generation,
        restore_root=tmp_path / "restored",
    )
    restored = AtomicFilesystemArtifactPayloadStore(tmp_path / "restored" / "cas")
    assert restored.load(first.descriptor.artifact_id) == first
    assert restored.load(second.descriptor.artifact_id) == second
    assert result.artifact_count == 2
    assert result.inspection_ready
    assert result.offline_replay_ready


def test_restore_requires_clean_destination(tmp_path: Path, resolved_flow) -> None:
    db_path = tmp_path / "runtime.duckdb"
    execution = DuckDBExecutionWriteStore(db_path)
    execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    manager = RuntimeBackupManager(
        database_path=db_path,
        payload_store=AtomicFilesystemArtifactPayloadStore(tmp_path / "cas"),
    )
    generation, _manifest = manager.create_backup(
        backup_id="backup-empty",
        destination_root=tmp_path / "backups",
        created_at="2026-08-22T00:00:00+00:00",
    )
    restore_root = tmp_path / "existing"
    restore_root.mkdir()
    with pytest.raises(BackupIntegrityError, match="must not already exist"):
        RuntimeBackupManager.restore(
            backup_generation=generation,
            restore_root=restore_root,
        )
