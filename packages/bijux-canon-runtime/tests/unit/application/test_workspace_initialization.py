# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3

import duckdb
import pytest

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import materialize_model
from bijux_canon_runtime.application import workspace_initialization
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    WorkspaceInitializationError,
    WorkspaceInitializationErrorCode,
    WorkspaceInitializationStatus,
    initialize_runtime_workspace,
    validate_runtime_workspace,
)
from bijux_canon_runtime.model.artifact import canonical_json_bytes


def _materialized_model(tmp_path: Path) -> Path:
    cache_root = tmp_path / "model-cache"
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch_artifact(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    materialize_model(
        LOCAL_MINILM_PROFILE,
        cache_root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch_artifact,
    )
    return cache_root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision


def _configuration(workspace: Path, model: Path, **extra: object):
    return resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "working_root": workspace,
            **extra,
        }
    )


def test_model_free_workspace_initialization_is_repeatable_and_valid(
    tmp_path: Path,
) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "lexical-workspace"}
    )

    initialized = initialize_runtime_workspace(configuration)
    validated = validate_runtime_workspace(configuration)
    repeated = initialize_runtime_workspace(configuration)

    assert initialized.status is WorkspaceInitializationStatus.INITIALIZED
    assert validated.status is WorkspaceInitializationStatus.UNCHANGED
    assert repeated == validated
    assert initialized.model_lock_artifact_id.startswith("sha256:")
    assert not configuration.require_workspace_layout().model_root.exists()


def _install_known_v1_layout(configuration) -> bytes:
    layout = configuration.require_workspace_layout()
    current = json.loads(layout.manifest_path.read_bytes())
    legacy_layout = workspace_initialization._legacy_layout_record(layout)
    legacy_configuration = workspace_initialization._legacy_configuration_record(
        configuration,
        legacy_layout,
    )
    configuration_id = str(legacy_configuration["identity_sha256"])
    layout_id = str(legacy_layout["identity_sha256"])
    model_lock_id = str(current["model_lock_artifact_id"])
    manifest = {
        "configuration": legacy_configuration,
        "configuration_identity_sha256": configuration_id,
        "created_at": current["created_at"],
        "layout": legacy_layout,
        "layout_identity_sha256": layout_id,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": "bijux.runtime.workspace.v1",
        "workspace_id": workspace_initialization._legacy_workspace_id(
            configuration_identity_sha256=configuration_id,
            layout_identity_sha256=layout_id,
            model_lock_id=model_lock_id,
        ),
        "workspace_version": 1,
    }
    content = canonical_json_bytes(manifest)
    layout.manifest_path.write_bytes(content)
    layout.migration_ledger_path.unlink()
    return content


def _install_known_v2_layout(configuration) -> tuple[bytes, bytes]:
    layout = configuration.require_workspace_layout()
    current = json.loads(layout.manifest_path.read_bytes())
    legacy_layout = workspace_initialization._legacy_v2_layout_record(layout)
    legacy_configuration = workspace_initialization._legacy_v2_configuration_record(
        configuration,
        legacy_layout,
    )
    configuration_id = str(legacy_configuration["identity_sha256"])
    layout_id = str(legacy_layout["identity_sha256"])
    model_lock_id = str(current["model_lock_artifact_id"])
    workspace_id = workspace_initialization._workspace_id_for_version(
        configuration_identity_sha256=configuration_id,
        layout_identity_sha256=layout_id,
        model_lock_id=model_lock_id,
        workspace_version=2,
    )
    ledger = workspace_initialization._migration_ledger(
        workspace_id=workspace_id,
        migrations=[],
    )
    manifest = workspace_initialization._legacy_v2_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(current["created_at"]),
    )
    manifest_content = canonical_json_bytes(manifest)
    ledger_content = canonical_json_bytes(ledger)
    layout.manifest_path.write_bytes(manifest_content)
    layout.migration_ledger_path.write_bytes(ledger_content)
    return manifest_content, ledger_content


def _install_known_v3_layout(configuration) -> tuple[bytes, bytes]:
    layout = configuration.require_workspace_layout()
    current = json.loads(layout.manifest_path.read_bytes())
    model_lock_id = str(current["model_lock_artifact_id"])
    legacy_layout = workspace_initialization._legacy_v3_layout_record(layout)
    legacy_configuration = workspace_initialization._configuration_record_for_layout(
        configuration,
        legacy_layout,
        retrieval_policy_id=("bijux.canon.index.hybrid-retrieval.content-evidence-v1"),
    )
    workspace_id = workspace_initialization._workspace_id_for_version(
        configuration_identity_sha256=str(legacy_configuration["identity_sha256"]),
        layout_identity_sha256=str(legacy_layout["identity_sha256"]),
        model_lock_id=model_lock_id,
        workspace_version=3,
    )
    ledger = workspace_initialization._migration_ledger(
        workspace_id=workspace_id,
        migrations=[],
    )
    manifest = workspace_initialization._legacy_v3_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(current["created_at"]),
        retrieval_policy_id=("bijux.canon.index.hybrid-retrieval.content-evidence-v1"),
    )
    manifest_content = canonical_json_bytes(manifest)
    ledger_content = canonical_json_bytes(ledger)
    layout.manifest_path.write_bytes(manifest_content)
    layout.migration_ledger_path.write_bytes(ledger_content)
    return manifest_content, ledger_content


def _install_known_v4_layout(configuration) -> tuple[bytes, bytes]:
    layout = configuration.require_workspace_layout()
    current = json.loads(layout.manifest_path.read_bytes())
    model_lock_id = str(current["model_lock_artifact_id"])
    legacy_layout = workspace_initialization._legacy_v4_layout_record(layout)
    legacy_configuration = workspace_initialization._configuration_record_for_layout(
        configuration,
        legacy_layout,
        retrieval_policy_id=configuration.retrieval_policy_id,
    )
    workspace_id = workspace_initialization._workspace_id_for_version(
        configuration_identity_sha256=str(legacy_configuration["identity_sha256"]),
        layout_identity_sha256=str(legacy_layout["identity_sha256"]),
        model_lock_id=model_lock_id,
        workspace_version=4,
    )
    ledger = workspace_initialization._migration_ledger(
        workspace_id=workspace_id,
        migrations=[],
    )
    manifest = workspace_initialization._legacy_v4_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(current["created_at"]),
    )
    manifest_content = canonical_json_bytes(manifest)
    ledger_content = canonical_json_bytes(ledger)
    layout.manifest_path.write_bytes(manifest_content)
    layout.migration_ledger_path.write_bytes(ledger_content)
    return manifest_content, ledger_content


def test_fresh_initialization_is_atomic_and_repeat_is_exact_noop(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)

    first = initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    manifest_bytes = layout.manifest_path.read_bytes()
    state = {
        path.relative_to(workspace).as_posix(): path.stat().st_mtime_ns
        for path in workspace.rglob("*")
    }
    second = initialize_runtime_workspace(configuration)
    validated = validate_runtime_workspace(configuration)

    assert first.status is WorkspaceInitializationStatus.INITIALIZED
    assert second.status is WorkspaceInitializationStatus.UNCHANGED
    assert validated == second
    assert second.workspace_id == first.workspace_id
    assert second.model_lock_artifact_id == first.model_lock_artifact_id
    assert layout.manifest_path.read_bytes() == manifest_bytes
    assert {
        path.relative_to(workspace).as_posix(): path.stat().st_mtime_ns
        for path in workspace.rglob("*")
    } == state
    assert layout.database_path.is_file()
    assert layout.job_store_path.is_file()
    assert layout.migration_ledger_path.is_file()
    assert layout.cas_root.is_dir()
    assert layout.index_root.is_dir()
    assert not list(tmp_path.glob(".workspace.*.initializing"))


def test_known_v1_workspace_is_backed_up_migrated_and_not_reapplied(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest = _install_known_v1_layout(configuration)
    database_before = layout.database_path.read_bytes()
    jobs_before = layout.job_store_path.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as validation:
        validate_runtime_workspace(configuration)
    assert (
        validation.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_VERSION
    )
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert not layout.migration_ledger_path.exists()

    migrated = initialize_runtime_workspace(configuration)
    manifest_after = layout.manifest_path.read_bytes()
    ledger_after = layout.migration_ledger_path.read_bytes()
    migration_ledger = json.loads(ledger_after)

    assert migrated.status is WorkspaceInitializationStatus.MIGRATED
    assert migrated.workspace_version == 5
    assert len(migrated.applied_migration_ids) == 4
    assert migrated.rollback_backup_path is not None
    backup = Path(migrated.rollback_backup_path)
    assert (backup / "workspace.json").read_bytes() == legacy_manifest
    assert (backup / "backup.json").is_file()
    assert len(migration_ledger["migrations"]) == 4
    assert (
        migration_ledger["migrations"][0]["migration_id"]
        == migrated.applied_migration_ids[0]
    )
    assert layout.database_path.read_bytes() == database_before
    assert layout.job_store_path.read_bytes() == jobs_before

    repeated = initialize_runtime_workspace(configuration)
    assert repeated.status is WorkspaceInitializationStatus.UNCHANGED
    assert layout.manifest_path.read_bytes() == manifest_after
    assert layout.migration_ledger_path.read_bytes() == ledger_after
    assert (
        len(tuple((layout.backup_root / "workspace-migrations/generations").iterdir()))
        == 4
    )


def test_interrupted_manifest_activation_resumes_from_bound_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest = _install_known_v1_layout(configuration)
    real_replace = os.replace
    replacements = 0

    def interrupt_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("simulated manifest activation interruption")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", interrupt_second_replace)
    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert layout.migration_ledger_path.is_file()

    monkeypatch.setattr(os, "replace", real_replace)
    recovered = initialize_runtime_workspace(configuration)
    assert recovered.status is WorkspaceInitializationStatus.MIGRATED
    assert validate_runtime_workspace(configuration).workspace_version == 5


def test_known_v2_workspace_is_backed_up_and_binds_retrieval_policy(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest, legacy_ledger = _install_known_v2_layout(configuration)

    migrated = initialize_runtime_workspace(configuration)

    assert migrated.status is WorkspaceInitializationStatus.MIGRATED
    assert migrated.workspace_version == 5
    assert len(migrated.applied_migration_ids) == 3
    assert migrated.rollback_backup_path is not None
    backup = Path(migrated.rollback_backup_path)
    assert (backup / "workspace.json").read_bytes() == legacy_manifest
    assert (backup / "workspace-migrations.json").read_bytes() == legacy_ledger
    manifest = json.loads(layout.manifest_path.read_bytes())
    assert manifest["configuration"]["retrieval_policy_id"] == (
        configuration.retrieval_policy_id
    )
    assert validate_runtime_workspace(configuration).workspace_version == 5


def test_interrupted_v2_policy_migration_resumes_from_bound_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest, _legacy_ledger = _install_known_v2_layout(configuration)
    real_replace = os.replace
    replacements = 0

    def interrupt_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("simulated policy manifest activation interruption")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", interrupt_second_replace)
    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE
    assert layout.manifest_path.read_bytes() == legacy_manifest

    monkeypatch.setattr(os, "replace", real_replace)
    recovered = initialize_runtime_workspace(configuration)
    assert recovered.status is WorkspaceInitializationStatus.MIGRATED
    assert recovered.workspace_version == 5
    assert validate_runtime_workspace(configuration).status is (
        WorkspaceInitializationStatus.UNCHANGED
    )


def test_known_v3_workspace_activates_content_evidence_policy_with_backup(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest, legacy_ledger = _install_known_v3_layout(configuration)

    migrated = initialize_runtime_workspace(configuration)

    assert migrated.status is WorkspaceInitializationStatus.MIGRATED
    assert migrated.workspace_version == 5
    assert len(migrated.applied_migration_ids) == 2
    assert migrated.rollback_backup_path is not None
    backup = Path(migrated.rollback_backup_path)
    assert (backup / "workspace.json").read_bytes() == legacy_manifest
    assert (backup / "workspace-migrations.json").read_bytes() == legacy_ledger
    manifest = json.loads(layout.manifest_path.read_bytes())
    assert manifest["configuration"]["retrieval_policy_id"] == (
        "bijux.canon.index.hybrid-retrieval.content-evidence-v2"
    )
    assert initialize_runtime_workspace(configuration).status is (
        WorkspaceInitializationStatus.UNCHANGED
    )


def test_interrupted_v3_policy_activation_resumes_from_bound_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest, _legacy_ledger = _install_known_v3_layout(configuration)
    real_replace = os.replace
    replacements = 0

    def interrupt_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("simulated content policy activation interruption")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", interrupt_second_replace)
    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE
    assert layout.manifest_path.read_bytes() == legacy_manifest

    monkeypatch.setattr(os, "replace", real_replace)
    recovered = initialize_runtime_workspace(configuration)
    assert recovered.status is WorkspaceInitializationStatus.MIGRATED
    assert recovered.workspace_version == 5
    assert validate_runtime_workspace(configuration).status is (
        WorkspaceInitializationStatus.UNCHANGED
    )


def test_known_v4_workspace_migrates_to_portable_logical_identity(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest, legacy_ledger = _install_known_v4_layout(configuration)

    migrated = initialize_runtime_workspace(configuration)

    assert migrated.status is WorkspaceInitializationStatus.MIGRATED
    assert migrated.workspace_version == 5
    assert migrated.applied_migration_ids == (
        workspace_initialization._V4_TO_V5_MIGRATION_ID,
    )
    assert migrated.rollback_backup_path is not None
    backup = Path(migrated.rollback_backup_path)
    assert (backup / "workspace.json").read_bytes() == legacy_manifest
    assert (backup / "workspace-migrations.json").read_bytes() == legacy_ledger
    manifest = json.loads(layout.manifest_path.read_bytes())
    assert manifest["schema_version"] == "bijux.runtime.workspace.v5"
    assert manifest["layout_identity_sha256"] == layout.identity_sha256
    assert manifest["workspace_id"] == migrated.workspace_id


def test_direct_workspace_relocation_names_the_incompatible_field_without_mutation(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    original_root = tmp_path / "original" / "workspace"
    initialize_runtime_workspace(_configuration(original_root, model))
    relocated_root = tmp_path / "relocated" / "workspace"
    shutil.copytree(original_root, relocated_root)
    relocated = _configuration(relocated_root, model)
    relocated_manifest = relocated.require_workspace_layout().manifest_path
    before = relocated_manifest.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(relocated)

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert "layout.root" in raised.value.detail
    assert "direct workspace relocation is unsupported" in raised.value.remediation
    assert relocated_manifest.read_bytes() == before


def test_v2_policy_migration_refuses_other_configuration_drift(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    original = _configuration(workspace, model)
    initialize_runtime_workspace(original)
    layout = original.require_workspace_layout()
    legacy_manifest, legacy_ledger = _install_known_v2_layout(original)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model, offline=False))

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert layout.migration_ledger_path.read_bytes() == legacy_ledger
    assert not (layout.backup_root / "workspace-migrations").exists()


def test_v1_migration_refuses_active_durable_jobs_before_backup(tmp_path: Path) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest = _install_known_v1_layout(configuration)
    with sqlite3.connect(layout.job_store_path) as jobs:
        jobs.execute(
            """
            INSERT INTO runtime_jobs (
                job_id, kind, idempotency_key, request_sha256, payload_json,
                status, cancel_requested, attempt_count, submitted_at,
                started_at, finished_at, deadline_at, timeout_seconds,
                result_json, error_type, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "job-active",
                "run",
                "active-migration-test",
                "sha256:request",
                "{}",
                "queued",
                0,
                0,
                "2026-08-23T00:00:00Z",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        )

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.WORKSPACE_BUSY
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert not (layout.backup_root / "workspace-migrations").exists()


def test_v1_migration_refuses_configuration_drift_before_backup(tmp_path: Path) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    original = _configuration(workspace, model)
    initialize_runtime_workspace(original)
    layout = original.require_workspace_layout()
    legacy_manifest = _install_known_v1_layout(original)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model, offline=False))

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert not (layout.backup_root / "workspace-migrations").exists()


def test_tampered_migration_backup_refuses_before_manifest_activation(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    legacy_manifest = _install_known_v1_layout(configuration)
    backup, _record = workspace_initialization._ensure_v1_migration_backup(
        layout,
        legacy_manifest,
    )
    (backup / "backup.json").write_text("{}", encoding="utf-8")

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.CORRUPT_STATE
    assert layout.manifest_path.read_bytes() == legacy_manifest
    assert not layout.migration_ledger_path.exists()


def test_tampered_migration_ledger_is_refused_without_repair(tmp_path: Path) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    ledger = json.loads(layout.migration_ledger_path.read_bytes())
    ledger["ledger_sha256"] = "sha256:" + "0" * 64
    tampered = canonical_json_bytes(ledger)
    layout.migration_ledger_path.write_bytes(tampered)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.CORRUPT_MANIFEST
    assert layout.migration_ledger_path.read_bytes() == tampered


def test_migrated_workspace_refuses_a_tampered_rollback_backup(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    _install_known_v1_layout(configuration)
    migrated = initialize_runtime_workspace(configuration)
    assert migrated.rollback_backup_path is not None
    manifest_path = configuration.require_workspace_layout().manifest_path
    activated_manifest = manifest_path.read_bytes()
    backup_manifest = Path(migrated.rollback_backup_path) / "backup.json"
    backup_manifest.write_text("{}", encoding="utf-8")

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.CORRUPT_STATE
    assert manifest_path.read_bytes() == activated_manifest


def test_existing_workspace_refuses_configuration_change_without_mutation(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    original = _configuration(workspace, model)
    initialize_runtime_workspace(original)
    before = original.require_workspace_layout().manifest_path.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model, offline=False))

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert "configuration.offline" in raised.value.detail
    assert original.require_workspace_layout().manifest_path.read_bytes() == before


def test_compatible_configuration_accepts_a_different_precedence_source(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    explicit = _configuration(workspace, model)
    initialized = initialize_runtime_workspace(explicit)
    from_environment = resolve_runtime_configuration(
        environment={
            "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH": str(model),
            "BIJUX_CANON_RUNTIME_WORKING_ROOT": str(workspace),
        }
    )

    validated = validate_runtime_workspace(from_environment)

    assert validated.workspace_id == initialized.workspace_id
    assert validated.status is WorkspaceInitializationStatus.UNCHANGED


def test_partial_workspace_is_refused_without_filling_missing_state(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    marker = workspace / "owned.txt"
    marker.write_text("preserve", encoding="utf-8")

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert sorted(path.name for path in workspace.iterdir()) == ["owned.txt"]


@pytest.mark.parametrize("unsupported_version", [0, 99])
def test_incompatible_workspace_version_is_typed_and_non_mutating(
    tmp_path: Path,
    unsupported_version: int,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    manifest_path = configuration.require_workspace_layout().manifest_path
    manifest = json.loads(manifest_path.read_bytes())
    manifest["workspace_version"] = unsupported_version
    changed = canonical_json_bytes(manifest)
    manifest_path.write_bytes(changed)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_VERSION
    assert manifest_path.read_bytes() == changed
    assert not (
        configuration.require_workspace_layout().backup_root / "workspace-migrations"
    ).exists()


def test_manifest_content_cannot_diverge_from_its_recorded_identity(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    manifest_path = configuration.require_workspace_layout().manifest_path
    manifest = json.loads(manifest_path.read_bytes())
    manifest["configuration"]["offline"] = False
    changed = canonical_json_bytes(manifest)
    manifest_path.write_bytes(changed)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert (
        raised.value.code is WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION
    )
    assert manifest_path.read_bytes() == changed


@pytest.mark.parametrize("store_kind", ["duckdb", "jobs"])
def test_corrupt_state_store_is_refused_without_repair(
    tmp_path: Path,
    store_kind: str,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    configuration = _configuration(workspace, model)
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    if store_kind == "duckdb":
        with duckdb.connect(str(layout.database_path)) as connection:
            connection.execute(
                "UPDATE schema_migrations SET checksum = 'tampered' WHERE version = 1"
            )
        changed = layout.database_path.read_bytes()
    else:
        with sqlite3.connect(layout.job_store_path) as connection:
            connection.execute("DROP TABLE runtime_jobs")
        changed = layout.job_store_path.read_bytes()

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(configuration)

    assert raised.value.code is WorkspaceInitializationErrorCode.CORRUPT_STATE
    changed_path = (
        layout.database_path if store_kind == "duckdb" else layout.job_store_path
    )
    assert changed_path.read_bytes() == changed


def test_missing_model_refuses_before_creating_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(
            _configuration(workspace, tmp_path / "missing-model")
        )

    assert raised.value.code is WorkspaceInitializationErrorCode.MODEL_UNAVAILABLE
    assert not workspace.exists()


def test_external_runtime_state_path_is_refused_without_side_effects(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"
    database = tmp_path / "external" / "runtime.duckdb"

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(
            _configuration(workspace, model, database_path=database)
        )

    assert raised.value.code is WorkspaceInitializationErrorCode.EXTERNAL_STATE_PATH
    assert not workspace.exists()
    assert not database.exists()


def test_activation_failure_removes_staging_and_leaves_no_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"

    def refuse_activation(_source: Path, _destination: Path) -> None:
        raise PermissionError("activation denied")

    monkeypatch.setattr(os, "rename", refuse_activation)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.UNWRITABLE
    assert not workspace.exists()
    assert not list(tmp_path.glob(".workspace.*.initializing"))


def test_workspace_root_symlink_is_refused_without_touching_target(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    workspace = tmp_path / "workspace"
    workspace.symlink_to(target, target_is_directory=True)

    with pytest.raises(WorkspaceInitializationError) as raised:
        initialize_runtime_workspace(_configuration(workspace, model))

    assert raised.value.code is WorkspaceInitializationErrorCode.UNSAFE_PATH
    assert list(target.iterdir()) == []


def test_initialization_failure_cleans_staging_after_constructor_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _materialized_model(tmp_path)
    workspace = tmp_path / "workspace"

    def crash(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("simulated constructor crash")

    monkeypatch.setattr(workspace_initialization, "_initialize_staging", crash)

    with pytest.raises(RuntimeError, match="constructor crash"):
        initialize_runtime_workspace(_configuration(workspace, model))

    assert not workspace.exists()
    assert not list(tmp_path.glob(".workspace.*.initializing"))
