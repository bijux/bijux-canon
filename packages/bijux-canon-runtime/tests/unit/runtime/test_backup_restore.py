from __future__ import annotations

from pathlib import Path

import pytest

from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    initialize_runtime_workspace,
    validate_runtime_workspace,
)
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
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)


def test_backup_restore_copies_only_reachable_payloads_and_verifies_identity(
    tmp_path: Path,
    resolved_flow,
) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "workspace"}
    )
    initialized = initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    db_path = layout.database_path
    execution = DuckDBExecutionWriteStore(db_path)
    run_id = execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    store = AtomicFilesystemArtifactPayloadStore(layout.cas_root)
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
    admitted_control = AddressedArtifact.from_json(
        {"transition": "retained for audit"},
        schema_id="bijux.runtime.scheduler-transition.v1",
        producer="bijux-canon-runtime:scheduler",
    )
    AuthoritativeArtifactPayloadStore(
        payload_store=store,
        database_path=db_path,
    ).put(admitted_control)
    manager = RuntimeBackupManager(configuration=configuration)

    generation, manifest = manager.create_backup(
        backup_id="backup-a",
        destination_root=tmp_path / "backups",
        created_at="2026-08-22T00:00:02+00:00",
    )

    assert manifest.artifact_ids == tuple(
        sorted(
            (
                admitted_control.descriptor.artifact_id,
                first.descriptor.artifact_id,
                second.descriptor.artifact_id,
            )
        )
    )
    backup_store = AtomicFilesystemArtifactPayloadStore(generation / "cas")
    assert backup_store.load(first.descriptor.artifact_id) == first
    assert backup_store.load(second.descriptor.artifact_id) == second
    assert backup_store.load(admitted_control.descriptor.artifact_id) == (
        admitted_control
    )
    with pytest.raises(KeyError):
        backup_store.load(orphan.descriptor.artifact_id)

    result = RuntimeBackupManager.restore(
        backup_generation=generation,
        restore_root=tmp_path / "restored",
    )
    restored = AtomicFilesystemArtifactPayloadStore(tmp_path / "restored" / "cas")
    assert restored.load(first.descriptor.artifact_id) == first
    assert restored.load(second.descriptor.artifact_id) == second
    assert restored.load(admitted_control.descriptor.artifact_id) == admitted_control
    assert result.artifact_count == 3
    assert result.inspection_ready
    assert result.offline_replay_ready
    restored_configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "restored"}
    )
    restored_workspace = validate_runtime_workspace(restored_configuration)
    assert restored_workspace.workspace_id == initialized.workspace_id


def test_restore_requires_clean_destination(tmp_path: Path, resolved_flow) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "workspace"}
    )
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    db_path = layout.database_path
    execution = DuckDBExecutionWriteStore(db_path)
    execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()
    manager = RuntimeBackupManager(configuration=configuration)
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


def test_configured_backup_uses_workspace_database_cas_and_backup_root(
    tmp_path: Path,
    resolved_flow,
) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "workspace"}
    )
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    execution = DuckDBExecutionWriteStore(layout.database_path)
    execution.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    execution._store.close()

    generation, manifest = RuntimeBackupManager(
        configuration=configuration
    ).create_workspace_backup(
        backup_id="configured-backup",
        created_at="2026-08-23T00:00:00+00:00",
    )

    assert generation == layout.backup_root / "generations" / "configured-backup"
    assert manifest.backup_id == "configured-backup"
    assert (generation / "runtime.duckdb").is_file()


@pytest.mark.parametrize("backup_id", ["../escape", "nested/escape", "", " space"])
def test_backup_identity_cannot_escape_the_generation_root(
    tmp_path: Path, backup_id: str
) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "workspace"}
    )
    manager = RuntimeBackupManager(configuration=configuration)

    with pytest.raises(ValueError, match="backup_id must be"):
        manager.create_backup(
            backup_id=backup_id,
            destination_root=tmp_path / "backups",
            created_at="2026-08-23T00:00:00+00:00",
        )

    assert not (tmp_path / "escape").exists()
