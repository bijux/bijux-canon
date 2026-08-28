# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Atomic initialization and validation of one Runtime workspace."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from bijux_canon_index.application import (
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID,
    CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID,
    IndexService,
)
from bijux_canon_index.infra.embeddings.model_cache import (
    ModelMaterializationError,
    load_model_lock,
    verify_materialized_model,
)
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    RuntimeWorkspaceLayout,
)
from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobHandler,
    DurableJobManager,
    DurableJobRequest,
    JobKind,
)
from bijux_canon_runtime.runtime.persistence.authoritative_payload_store import (
    AuthoritativeArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)


class WorkspaceInitializationErrorCode(StrEnum):
    """Stable initialization refusal categories."""

    CORRUPT_MANIFEST = "corrupt_manifest"
    CORRUPT_STATE = "corrupt_state"
    EXTERNAL_STATE_PATH = "external_state_path"
    INCOMPATIBLE_CONFIGURATION = "incompatible_configuration"
    INCOMPATIBLE_VERSION = "incompatible_version"
    MODEL_UNAVAILABLE = "model_unavailable"
    NOT_INITIALIZED = "not_initialized"
    PARTIAL_WORKSPACE = "partial_workspace"
    UNSAFE_PATH = "unsafe_path"
    UNWRITABLE = "unwritable"
    WORKSPACE_BUSY = "workspace_busy"


class WorkspaceInitializationError(ConfigurationError):
    """A workspace could not be initialized or validated without mutation."""

    def __init__(
        self,
        code: WorkspaceInitializationErrorCode,
        detail: str,
        remediation: str,
    ) -> None:
        self.code = code
        self.detail = detail
        self.remediation = remediation
        super().__init__(f"{code.value}: {detail}; {remediation}")


class WorkspaceInitializationStatus(StrEnum):
    """Stable successful initialization outcomes."""

    INITIALIZED = "initialized"
    MIGRATED = "migrated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class WorkspaceInitializationResult:
    """Safe operator summary for one initialized workspace."""

    configuration_identity_sha256: str
    layout_identity_sha256: str
    model_lock_artifact_id: str
    status: WorkspaceInitializationStatus
    workspace_id: str
    workspace_root: str
    workspace_version: int
    applied_migration_ids: tuple[str, ...] = ()
    rollback_backup_path: str | None = None
    schema_version: str = "bijux.runtime.workspace-initialization-result.v2"

    def record(self) -> dict[str, object]:
        """Return stable JSON output without secret values."""
        return {
            "configuration_identity_sha256": self.configuration_identity_sha256,
            "applied_migration_ids": list(self.applied_migration_ids),
            "layout_identity_sha256": self.layout_identity_sha256,
            "model_lock_artifact_id": self.model_lock_artifact_id,
            "rollback_backup_path": self.rollback_backup_path,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "workspace_root": self.workspace_root,
            "workspace_version": self.workspace_version,
        }


_MIGRATION_LEDGER_SCHEMA = "bijux.runtime.workspace-migrations.v1"
_WORKSPACE_MANIFEST_SCHEMA = "bijux.runtime.workspace.v5"
_LEGACY_V4_WORKSPACE_MANIFEST_SCHEMA = "bijux.runtime.workspace.v4"
_LEGACY_V3_WORKSPACE_MANIFEST_SCHEMA = "bijux.runtime.workspace.v3"
_LEGACY_V2_WORKSPACE_MANIFEST_SCHEMA = "bijux.runtime.workspace.v2"
_LEGACY_WORKSPACE_MANIFEST_SCHEMA = "bijux.runtime.workspace.v1"
_V1_TO_V2_MIGRATION_RECORD = {
    "from_version": 1,
    "name": "record-workspace-migration-lineage",
    "schema_version": "bijux.runtime.workspace-migration.v1",
    "to_version": 2,
}
_V1_TO_V2_MIGRATION_ID = (
    "sha256:"
    + hashlib.sha256(canonical_json_bytes(_V1_TO_V2_MIGRATION_RECORD)).hexdigest()
)
_V2_TO_V3_MIGRATION_RECORD = {
    "from_version": 2,
    "name": "bind-retrieval-policy-configuration",
    "schema_version": "bijux.runtime.workspace-migration.v1",
    "to_version": 3,
}
_V2_TO_V3_MIGRATION_ID = (
    "sha256:"
    + hashlib.sha256(canonical_json_bytes(_V2_TO_V3_MIGRATION_RECORD)).hexdigest()
)
_V3_TO_V4_MIGRATION_RECORD = {
    "from_version": 3,
    "name": "activate-content-evidence-planning-policy",
    "schema_version": "bijux.runtime.workspace-migration.v1",
    "to_version": 4,
}
_V3_TO_V4_MIGRATION_ID = (
    "sha256:"
    + hashlib.sha256(canonical_json_bytes(_V3_TO_V4_MIGRATION_RECORD)).hexdigest()
)
_V4_TO_V5_MIGRATION_RECORD = {
    "from_version": 4,
    "name": "separate-logical-identity-from-local-locations",
    "schema_version": "bijux.runtime.workspace-migration.v1",
    "to_version": 5,
}
_V4_TO_V5_MIGRATION_ID = (
    "sha256:"
    + hashlib.sha256(canonical_json_bytes(_V4_TO_V5_MIGRATION_RECORD)).hexdigest()
)
_MIGRATION_IDS = {
    1: _V1_TO_V2_MIGRATION_ID,
    2: _V2_TO_V3_MIGRATION_ID,
    3: _V3_TO_V4_MIGRATION_ID,
    4: _V4_TO_V5_MIGRATION_ID,
}


def _content_sha256(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _record_identity(record: Mapping[str, object]) -> str:
    return _content_sha256(canonical_json_bytes(record))


NO_MODEL_LOCK_ARTIFACT_ID = _record_identity(
    {
        "capability": "embedding-model",
        "schema_version": "bijux.runtime.absent-capability.v1",
        "status": "not-configured",
    }
)


def _migration_ledger(
    *,
    workspace_id: str,
    migrations: list[dict[str, object]],
) -> dict[str, object]:
    unsigned: dict[str, object] = {
        "migrations": migrations,
        "schema_version": _MIGRATION_LEDGER_SCHEMA,
        "workspace_id": workspace_id,
    }
    return {**unsigned, "ledger_sha256": _record_identity(unsigned)}


def _workspace_identity(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
) -> str:
    payload = canonical_json_bytes(
        {
            "configuration_identity_sha256": configuration.identity_sha256,
            "layout_identity_sha256": layout.identity_sha256,
            "model_lock_artifact_id": model_lock_id,
            "schema_version": "bijux.runtime.workspace-identity.v1",
            "workspace_version": layout.workspace_version,
        }
    )
    return "workspace_v1_" + hashlib.sha256(payload).hexdigest()


def _manifest_record(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    migration_ledger_sha256: str,
    *,
    created_at: str | None = None,
) -> dict[str, object]:
    return {
        "configuration": configuration.redacted_record(),
        "configuration_identity_sha256": configuration.identity_sha256,
        "created_at": created_at
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "layout": layout.record(),
        "layout_identity_sha256": layout.identity_sha256,
        "migration_ledger_sha256": migration_ledger_sha256,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": _WORKSPACE_MANIFEST_SCHEMA,
        "workspace_id": _workspace_identity(configuration, layout, model_lock_id),
        "workspace_version": layout.workspace_version,
    }


def _configuration_authority_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    authority_fields = (
        "identity_sha256",
        "offline",
        "provider_api_key_ref",
        "resource_budget",
        "retrieval_policy_id",
        "schema_version",
        "strict_determinism",
        "workspace_layout",
    )
    return {field: value.get(field) for field in authority_fields}


def _result(
    manifest: Mapping[str, object],
    layout: RuntimeWorkspaceLayout,
    status: WorkspaceInitializationStatus,
    *,
    applied_migration_ids: tuple[str, ...] = (),
    rollback_backup_path: str | None = None,
) -> WorkspaceInitializationResult:
    workspace_version = manifest["workspace_version"]
    if not isinstance(workspace_version, int):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest has an invalid version value",
            "restore a verified backup or select another workspace",
        )
    return WorkspaceInitializationResult(
        configuration_identity_sha256=str(manifest["configuration_identity_sha256"]),
        layout_identity_sha256=str(manifest["layout_identity_sha256"]),
        model_lock_artifact_id=str(manifest["model_lock_artifact_id"]),
        status=status,
        workspace_id=str(manifest["workspace_id"]),
        workspace_root=str(layout.root),
        workspace_version=workspace_version,
        applied_migration_ids=applied_migration_ids,
        rollback_backup_path=rollback_backup_path,
    )


def _load_manifest(path: Path) -> dict[str, object]:
    try:
        content = path.read_bytes()
        value = json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest is unreadable",
            "restore a verified backup or select another workspace",
        ) from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != content:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest is not canonical",
            "restore a verified backup or select another workspace",
        )
    return value


def _load_migration_ledger(path: Path, *, workspace_id: str) -> dict[str, object]:
    ledger = _load_manifest(path)
    unsigned = dict(ledger)
    ledger_sha256 = unsigned.pop("ledger_sha256", None)
    migrations = unsigned.get("migrations")
    if (
        set(ledger)
        != {
            "ledger_sha256",
            "migrations",
            "schema_version",
            "workspace_id",
        }
        or ledger.get("schema_version") != _MIGRATION_LEDGER_SCHEMA
        or ledger.get("workspace_id") != workspace_id
        or ledger_sha256 != _record_identity(unsigned)
        or not isinstance(migrations, list)
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace migration ledger identity is invalid",
            "restore the workspace manifest and migration ledger from one backup",
        )
    expected_from: int | None = None
    for migration in migrations:
        if not isinstance(migration, dict):
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "workspace migration ledger record is invalid",
                "restore the workspace manifest and migration ledger from one backup",
            )
        from_version = migration.get("from_version")
        if expected_from is None and isinstance(from_version, int):
            expected_from = from_version
        expected_id = _MIGRATION_IDS.get(expected_from or -1)
        if (
            set(migration)
            != {
                "applied_at",
                "backup_manifest_path",
                "backup_manifest_sha256",
                "from_version",
                "migration_id",
                "source_manifest_sha256",
                "to_version",
            }
            or expected_id is None
            or migration.get("migration_id") != expected_id
            or from_version != expected_from
            or migration.get("to_version") != (expected_from or -1) + 1
            or not all(
                isinstance(migration.get(field), str) and migration.get(field)
                for field in (
                    "applied_at",
                    "backup_manifest_path",
                    "backup_manifest_sha256",
                    "source_manifest_sha256",
                )
            )
        ):
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "workspace migration order or identity is invalid",
                "restore the workspace manifest and migration ledger from one backup",
            )
        assert expected_from is not None
        expected_from += 1
    return ledger


def _validate_migration_backups(
    layout: RuntimeWorkspaceLayout,
    ledger: Mapping[str, object],
) -> None:
    migrations = ledger["migrations"]
    assert isinstance(migrations, list)
    for migration in migrations:
        assert isinstance(migration, dict)
        relative_path = str(migration["backup_manifest_path"])
        candidate = layout.root / relative_path
        if candidate.is_symlink():
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.UNSAFE_PATH,
                "workspace migration backup manifest must not be a symbolic link",
                "restore a real backup file beneath the workspace backup root",
            )
        backup_manifest_path = candidate.resolve()
        try:
            backup_manifest_path.relative_to(layout.backup_root)
        except ValueError as exc:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.EXTERNAL_STATE_PATH,
                "workspace migration backup path escapes its backup authority",
                "restore the workspace manifest and ledger from a verified backup",
            ) from exc
        try:
            backup = _load_manifest(backup_manifest_path)
            unsigned = dict(backup)
            backup_sha256 = unsigned.pop("backup_manifest_sha256", None)
            source_manifest_path = backup_manifest_path.parent / "workspace.json"
            state_sha256 = backup.get("state_sha256")
            common_keys = {
                "backup_id",
                "backup_manifest_sha256",
                "created_at",
                "migration_id",
                "schema_version",
                "source_manifest_sha256",
                "state_sha256",
            }
            schema_version = backup.get("schema_version")
            expected_keys = set(common_keys)
            if schema_version == "bijux.runtime.workspace-migration-backup.v2":
                expected_keys.add("source_migration_ledger_sha256")
            if (
                set(backup) != expected_keys
                or schema_version
                not in {
                    "bijux.runtime.workspace-migration-backup.v1",
                    "bijux.runtime.workspace-migration-backup.v2",
                }
                or not isinstance(state_sha256, dict)
                or any(
                    not isinstance(name, str) or not isinstance(identity, str)
                    for name, identity in state_sha256.items()
                )
                or backup_sha256 != _record_identity(unsigned)
                or backup_sha256 != migration["backup_manifest_sha256"]
                or backup.get("migration_id") != migration["migration_id"]
                or backup.get("source_manifest_sha256")
                != migration["source_manifest_sha256"]
                or _hash_file(source_manifest_path)
                != migration["source_manifest_sha256"]
            ):
                raise ValueError
            if schema_version == "bijux.runtime.workspace-migration-backup.v2":
                source_ledger_path = (
                    backup_manifest_path.parent / "workspace-migrations.json"
                )
                if _hash_file(source_ledger_path) != backup.get(
                    "source_migration_ledger_sha256"
                ):
                    raise ValueError
        except (OSError, ValueError, WorkspaceInitializationError) as exc:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_STATE,
                "workspace migration rollback backup is missing or invalid",
                "restore the complete migration backup before opening this workspace",
            ) from exc


def _verify_model(layout: RuntimeWorkspaceLayout) -> str:
    try:
        lock = load_model_lock(layout.model_lock_path)
        verify_materialized_model(layout.model_root, lock)
    except ModelMaterializationError as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.MODEL_UNAVAILABLE,
            "the configured local model is missing or does not match its lock",
            str(exc),
        ) from exc
    return lock.lock_id


def _configured_model_lock_id(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
) -> str:
    if configuration.embedding_model_path is None:
        return NO_MODEL_LOCK_ARTIFACT_ID
    return _verify_model(layout)


def _state_path(layout: RuntimeWorkspaceLayout, path: Path) -> Path:
    try:
        path.relative_to(layout.root)
    except ValueError as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.EXTERNAL_STATE_PATH,
            f"workspace-owned state is outside the workspace: {path}",
            "use a path below --workspace; only the locked model may be external",
        ) from exc
    return path


def _validate_owned_paths(layout: RuntimeWorkspaceLayout) -> None:
    owned = (
        layout.manifest_path,
        layout.migration_ledger_path,
        layout.cas_root,
        layout.database_path,
        layout.job_store_path,
        layout.index_root,
        layout.operations_root,
        layout.vex_root,
        layout.locks_root,
        layout.staging_root,
        layout.temporary_root,
        layout.backup_root,
    )
    for path in owned:
        _state_path(layout, path)


def _staged_path(layout: RuntimeWorkspaceLayout, staging: Path, path: Path) -> Path:
    return staging / _state_path(layout, path).relative_to(layout.root)


def _hex_record_identity(record: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json_bytes(record)).hexdigest()


def _legacy_layout_record(layout: RuntimeWorkspaceLayout) -> dict[str, object]:
    record = layout.record(include_identity=False)
    record.pop("migration_ledger_path")
    record["schema_version"] = "bijux.runtime.workspace-layout.v1"
    record["workspace_version"] = 1
    record["identity_sha256"] = _hex_record_identity(record)
    return record


def _legacy_v2_layout_record(layout: RuntimeWorkspaceLayout) -> dict[str, object]:
    record = layout.record(include_identity=False)
    record["schema_version"] = "bijux.runtime.workspace-layout.v2"
    record["workspace_version"] = 2
    record["identity_sha256"] = _hex_record_identity(record)
    return record


def _legacy_v3_layout_record(layout: RuntimeWorkspaceLayout) -> dict[str, object]:
    record = layout.record(include_identity=False)
    record["schema_version"] = "bijux.runtime.workspace-layout.v3"
    record["workspace_version"] = 3
    record["identity_sha256"] = _hex_record_identity(record)
    return record


def _legacy_v4_layout_record(layout: RuntimeWorkspaceLayout) -> dict[str, object]:
    record = layout.record(include_identity=False)
    record["schema_version"] = "bijux.runtime.workspace-layout.v4"
    record["workspace_version"] = 4
    record["identity_sha256"] = _hex_record_identity(record)
    return record


def _legacy_configuration_record(
    configuration: RuntimeConfiguration,
    legacy_layout: Mapping[str, object],
) -> dict[str, object]:
    record = configuration.redacted_record()
    record.pop("retrieval_policy_id")
    origins = record.get("origins")
    if isinstance(origins, dict):
        origins.pop("retrieval_policy_id", None)
    identity_record: dict[str, object] = {
        "offline": configuration.offline,
        "provider_api_key_ref": (
            configuration.provider_api_key.environment_variable
            if configuration.provider_api_key is not None
            else None
        ),
        "resource_budget": record["resource_budget"],
        "schema_version": configuration.schema_version,
        "strict_determinism": configuration.strict_determinism,
        "workspace_layout": dict(legacy_layout),
    }
    record["identity_sha256"] = _hex_record_identity(identity_record)
    record["workspace_layout"] = dict(legacy_layout)
    return record


def _legacy_v2_configuration_record(
    configuration: RuntimeConfiguration,
    legacy_layout: Mapping[str, object],
) -> dict[str, object]:
    return _legacy_configuration_record(configuration, legacy_layout)


def _configuration_record_for_layout(
    configuration: RuntimeConfiguration,
    layout_record: Mapping[str, object],
    *,
    retrieval_policy_id: str,
) -> dict[str, object]:
    record = configuration.redacted_record()
    record["retrieval_policy_id"] = retrieval_policy_id
    identity_record: dict[str, object] = {
        "offline": configuration.offline,
        "provider_api_key_ref": (
            configuration.provider_api_key.environment_variable
            if configuration.provider_api_key is not None
            else None
        ),
        "resource_budget": record["resource_budget"],
        "retrieval_policy_id": retrieval_policy_id,
        "schema_version": configuration.schema_version,
        "strict_determinism": configuration.strict_determinism,
        "workspace_layout": dict(layout_record),
    }
    record["identity_sha256"] = _hex_record_identity(identity_record)
    record["workspace_layout"] = dict(layout_record)
    return record


def _legacy_workspace_id(
    *,
    configuration_identity_sha256: str,
    layout_identity_sha256: str,
    model_lock_id: str,
) -> str:
    payload = canonical_json_bytes(
        {
            "configuration_identity_sha256": configuration_identity_sha256,
            "layout_identity_sha256": layout_identity_sha256,
            "model_lock_artifact_id": model_lock_id,
            "schema_version": "bijux.runtime.workspace-identity.v1",
            "workspace_version": 1,
        }
    )
    return "workspace_v1_" + hashlib.sha256(payload).hexdigest()


def _workspace_id_for_version(
    *,
    configuration_identity_sha256: str,
    layout_identity_sha256: str,
    model_lock_id: str,
    workspace_version: int,
) -> str:
    payload = canonical_json_bytes(
        {
            "configuration_identity_sha256": configuration_identity_sha256,
            "layout_identity_sha256": layout_identity_sha256,
            "model_lock_artifact_id": model_lock_id,
            "schema_version": "bijux.runtime.workspace-identity.v1",
            "workspace_version": workspace_version,
        }
    )
    return "workspace_v1_" + hashlib.sha256(payload).hexdigest()


def _validate_workspace_state_paths(layout: RuntimeWorkspaceLayout) -> None:
    required_directories = (
        layout.cas_root,
        layout.index_root,
        layout.operations_root,
        layout.vex_root,
        layout.locks_root,
        layout.staging_root,
        layout.temporary_root,
        layout.backup_root,
    )
    if any(not path.is_dir() or path.is_symlink() for path in required_directories):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace is missing a required state directory",
            "restore a verified backup before retrying initialization",
        )
    if not layout.database_path.is_file() or not layout.job_store_path.is_file():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace is missing a required state database",
            "restore a verified backup before retrying initialization",
        )
    structural_paths = (
        layout.cas_root / "objects" / "sha256",
        layout.cas_root / "staging",
        layout.index_root / "generations",
        layout.index_root / "registry.lock",
    )
    if any(not path.exists() or path.is_symlink() for path in structural_paths):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace store structure is incomplete",
            "restore a verified backup before retrying initialization",
        )
    _validate_state_stores(layout)


def _validate_legacy_v1(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    manifest: Mapping[str, object],
) -> None:
    expected_keys = {
        "configuration",
        "configuration_identity_sha256",
        "created_at",
        "layout",
        "layout_identity_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    }
    legacy_layout = _legacy_layout_record(layout)
    legacy_configuration = _legacy_configuration_record(
        configuration,
        legacy_layout,
    )
    legacy_configuration_id = str(legacy_configuration["identity_sha256"])
    legacy_layout_id = str(legacy_layout["identity_sha256"])
    if (
        set(manifest) != expected_keys
        or not isinstance(manifest.get("created_at"), str)
        or manifest.get("schema_version") != _LEGACY_WORKSPACE_MANIFEST_SCHEMA
        or manifest.get("workspace_version") != 1
        or manifest.get("configuration_identity_sha256") != legacy_configuration_id
        or manifest.get("layout") != legacy_layout
        or manifest.get("layout_identity_sha256") != legacy_layout_id
        or manifest.get("model_lock_artifact_id") != model_lock_id
        or manifest.get("workspace_id")
        != _legacy_workspace_id(
            configuration_identity_sha256=legacy_configuration_id,
            layout_identity_sha256=legacy_layout_id,
            model_lock_id=model_lock_id,
        )
        or _configuration_authority_record(manifest.get("configuration"))
        != _configuration_authority_record(legacy_configuration)
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "legacy workspace identity or effective configuration differs",
            "use the original settings or restore the complete legacy workspace",
        )
    _validate_workspace_state_paths(layout)
    with sqlite3.connect(
        f"{layout.job_store_path.as_uri()}?mode=ro",
        uri=True,
    ) as jobs:
        active_jobs = int(
            jobs.execute(
                "SELECT count(*) FROM runtime_jobs "
                "WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
        )
    if active_jobs:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace migration requires zero queued or running jobs",
            "stop Runtime workers and finish or cancel active jobs before retrying",
        )


def _legacy_v2_manifest_record(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    migration_ledger_sha256: str,
    *,
    created_at: str,
) -> dict[str, object]:
    legacy_layout = _legacy_v2_layout_record(layout)
    legacy_configuration = _legacy_v2_configuration_record(
        configuration,
        legacy_layout,
    )
    configuration_id = str(legacy_configuration["identity_sha256"])
    layout_id = str(legacy_layout["identity_sha256"])
    return {
        "configuration": legacy_configuration,
        "configuration_identity_sha256": configuration_id,
        "created_at": created_at,
        "layout": legacy_layout,
        "layout_identity_sha256": layout_id,
        "migration_ledger_sha256": migration_ledger_sha256,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": _LEGACY_V2_WORKSPACE_MANIFEST_SCHEMA,
        "workspace_id": _workspace_id_for_version(
            configuration_identity_sha256=configuration_id,
            layout_identity_sha256=layout_id,
            model_lock_id=model_lock_id,
            workspace_version=2,
        ),
        "workspace_version": 2,
    }


def _legacy_v3_manifest_record(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    migration_ledger_sha256: str,
    *,
    created_at: str,
    retrieval_policy_id: str | None = None,
) -> dict[str, object]:
    legacy_layout = _legacy_v3_layout_record(layout)
    legacy_configuration = _configuration_record_for_layout(
        configuration,
        legacy_layout,
        retrieval_policy_id=(
            configuration.retrieval_policy_id
            if retrieval_policy_id is None
            else retrieval_policy_id
        ),
    )
    configuration_id = str(legacy_configuration["identity_sha256"])
    layout_id = str(legacy_layout["identity_sha256"])
    return {
        "configuration": legacy_configuration,
        "configuration_identity_sha256": configuration_id,
        "created_at": created_at,
        "layout": legacy_layout,
        "layout_identity_sha256": layout_id,
        "migration_ledger_sha256": migration_ledger_sha256,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": _LEGACY_V3_WORKSPACE_MANIFEST_SCHEMA,
        "workspace_id": _workspace_id_for_version(
            configuration_identity_sha256=configuration_id,
            layout_identity_sha256=layout_id,
            model_lock_id=model_lock_id,
            workspace_version=3,
        ),
        "workspace_version": 3,
    }


def _legacy_v4_manifest_record(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    migration_ledger_sha256: str,
    *,
    created_at: str,
) -> dict[str, object]:
    legacy_layout = _legacy_v4_layout_record(layout)
    legacy_configuration = _configuration_record_for_layout(
        configuration,
        legacy_layout,
        retrieval_policy_id=configuration.retrieval_policy_id,
    )
    configuration_id = str(legacy_configuration["identity_sha256"])
    layout_id = str(legacy_layout["identity_sha256"])
    return {
        "configuration": legacy_configuration,
        "configuration_identity_sha256": configuration_id,
        "created_at": created_at,
        "layout": legacy_layout,
        "layout_identity_sha256": layout_id,
        "migration_ledger_sha256": migration_ledger_sha256,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": _LEGACY_V4_WORKSPACE_MANIFEST_SCHEMA,
        "workspace_id": _workspace_id_for_version(
            configuration_identity_sha256=configuration_id,
            layout_identity_sha256=layout_id,
            model_lock_id=model_lock_id,
            workspace_version=4,
        ),
        "workspace_version": 4,
    }


def _validate_legacy_v2(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    manifest: Mapping[str, object],
    *,
    ledger_path: Path | None = None,
) -> dict[str, object]:
    expected_keys = {
        "configuration",
        "configuration_identity_sha256",
        "created_at",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    }
    if set(manifest) != expected_keys or not isinstance(
        manifest.get("created_at"), str
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-2 workspace manifest fields are invalid",
            "restore a verified backup before retrying migration",
        )
    workspace_id = manifest.get("workspace_id")
    if not isinstance(workspace_id, str):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-2 workspace identity is invalid",
            "restore a verified backup before retrying migration",
        )
    ledger = _load_migration_ledger(
        layout.migration_ledger_path if ledger_path is None else ledger_path,
        workspace_id=workspace_id,
    )
    _validate_migration_backups(layout, ledger)
    expected = _legacy_v2_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(manifest["created_at"]),
    )
    if _configuration_authority_record(
        manifest.get("configuration")
    ) != _configuration_authority_record(expected["configuration"]):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-2 workspace identity or effective configuration differs",
            "use the original settings or restore the complete workspace",
        )
    compatible_fields = (
        "configuration_identity_sha256",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    )
    if any(manifest.get(field) != expected[field] for field in compatible_fields):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-2 workspace identity or effective configuration differs",
            "use the original settings or restore the complete workspace",
        )
    _validate_workspace_state_paths(layout)
    with sqlite3.connect(
        f"{layout.job_store_path.as_uri()}?mode=ro",
        uri=True,
    ) as jobs:
        active_jobs = int(
            jobs.execute(
                "SELECT count(*) FROM runtime_jobs "
                "WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
        )
    if active_jobs:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace migration requires zero queued or running jobs",
            "stop Runtime workers and finish or cancel active jobs before retrying",
        )
    return ledger


def _validate_legacy_v3(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    manifest: Mapping[str, object],
    *,
    ledger_path: Path | None = None,
) -> dict[str, object]:
    expected_keys = {
        "configuration",
        "configuration_identity_sha256",
        "created_at",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    }
    raw_configuration = manifest.get("configuration")
    if (
        set(manifest) != expected_keys
        or not isinstance(manifest.get("created_at"), str)
        or not isinstance(raw_configuration, dict)
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-3 workspace manifest fields are invalid",
            "restore a verified backup before retrying migration",
        )
    source_policy = raw_configuration.get("retrieval_policy_id")
    allowed_policies = {configuration.retrieval_policy_id}
    if configuration.retrieval_policy_id == CONTENT_EVIDENCE_RETRIEVAL_POLICY_ID:
        allowed_policies.add(CONTENT_EVIDENCE_RETRIEVAL_POLICY_V1_ID)
    if not isinstance(source_policy, str) or source_policy not in allowed_policies:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-3 retrieval policy cannot be migrated to the requested policy",
            "use the original settings or initialize another workspace",
        )
    workspace_id = manifest.get("workspace_id")
    if not isinstance(workspace_id, str):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-3 workspace identity is invalid",
            "restore a verified backup before retrying migration",
        )
    ledger = _load_migration_ledger(
        layout.migration_ledger_path if ledger_path is None else ledger_path,
        workspace_id=workspace_id,
    )
    _validate_migration_backups(layout, ledger)
    expected = _legacy_v3_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(manifest["created_at"]),
        retrieval_policy_id=source_policy,
    )
    if _configuration_authority_record(
        raw_configuration
    ) != _configuration_authority_record(expected["configuration"]):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-3 workspace identity or effective configuration differs",
            "use the original settings or restore the complete workspace",
        )
    compatible_fields = (
        "configuration_identity_sha256",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    )
    if any(manifest.get(field) != expected[field] for field in compatible_fields):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-3 workspace identity or effective configuration differs",
            "use the original settings or restore the complete workspace",
        )
    _validate_workspace_state_paths(layout)
    with sqlite3.connect(
        f"{layout.job_store_path.as_uri()}?mode=ro",
        uri=True,
    ) as jobs:
        active_jobs = int(
            jobs.execute(
                "SELECT count(*) FROM runtime_jobs "
                "WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
        )
    if active_jobs:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace migration requires zero queued or running jobs",
            "stop Runtime workers and finish or cancel active jobs before retrying",
        )
    return ledger


def _layout_location_mismatches(
    recorded: object,
    expected: object,
) -> tuple[str, ...]:
    if not isinstance(recorded, dict) or not isinstance(expected, dict):
        return ("layout",)
    identity_fields = {"identity_sha256", "schema_version", "workspace_version"}
    return tuple(
        f"layout.{field}"
        for field in sorted(set(recorded) | set(expected))
        if field not in identity_fields and recorded.get(field) != expected.get(field)
    )


def _raise_location_mismatch(mismatches: tuple[str, ...]) -> None:
    if not mismatches:
        return
    if "layout.root" not in mismatches:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "workspace path configuration differs: " + ", ".join(mismatches),
            "use the recorded value for each named path field or initialize another "
            "workspace",
        )
    raise WorkspaceInitializationError(
        WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
        "workspace location differs: " + ", ".join(mismatches),
        "return the workspace to its recorded location; direct workspace relocation "
        "is unsupported in this release",
    )


def _configuration_authority_mismatches(
    recorded: object,
    expected: object,
) -> tuple[str, ...]:
    recorded_authority = _configuration_authority_record(recorded)
    expected_authority = _configuration_authority_record(expected)
    ignored = {"identity_sha256", "workspace_layout"}
    return tuple(
        f"configuration.{field}"
        for field in sorted(set(recorded_authority) | set(expected_authority))
        if field not in ignored
        and recorded_authority.get(field) != expected_authority.get(field)
    )


def _validate_legacy_v4(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    manifest: Mapping[str, object],
    *,
    ledger_path: Path | None = None,
) -> dict[str, object]:
    expected_keys = {
        "configuration",
        "configuration_identity_sha256",
        "created_at",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    }
    if set(manifest) != expected_keys or not isinstance(
        manifest.get("created_at"), str
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-4 workspace manifest fields are invalid",
            "restore a verified backup before retrying migration",
        )
    workspace_id = manifest.get("workspace_id")
    if not isinstance(workspace_id, str):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "version-4 workspace identity is invalid",
            "restore a verified backup before retrying migration",
        )
    ledger = _load_migration_ledger(
        layout.migration_ledger_path if ledger_path is None else ledger_path,
        workspace_id=workspace_id,
    )
    _validate_migration_backups(layout, ledger)
    expected = _legacy_v4_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(manifest["created_at"]),
    )
    _raise_location_mismatch(
        _layout_location_mismatches(manifest.get("layout"), expected["layout"])
    )
    if _configuration_authority_record(
        manifest.get("configuration")
    ) != _configuration_authority_record(expected["configuration"]):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-4 workspace effective configuration differs",
            "use the original settings or initialize another workspace",
        )
    compatible_fields = (
        "configuration_identity_sha256",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    )
    if any(manifest.get(field) != expected[field] for field in compatible_fields):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "version-4 workspace identity or effective configuration differs",
            "use the original settings or restore the complete workspace",
        )
    _validate_workspace_state_paths(layout)
    with sqlite3.connect(
        f"{layout.job_store_path.as_uri()}?mode=ro",
        uri=True,
    ) as jobs:
        active_jobs = int(
            jobs.execute(
                "SELECT count(*) FROM runtime_jobs "
                "WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
        )
    if active_jobs:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace migration requires zero queued or running jobs",
            "stop Runtime workers and finish or cancel active jobs before retrying",
        )
    return ledger


class _NoopDurableJobHandler:
    def __call__(
        self,
        request: DurableJobRequest,
        is_cancelled: Callable[[], bool],
    ) -> Mapping[str, object]:
        del request, is_cancelled
        return {}


def _initialize_staging(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    staging: Path,
    model_lock_id: str,
) -> dict[str, object]:
    directory_paths = (
        layout.operations_root,
        layout.vex_root,
        layout.locks_root,
        layout.staging_root,
        layout.temporary_root,
        layout.backup_root,
    )
    for path in directory_paths:
        _staged_path(layout, staging, path).mkdir(parents=True, exist_ok=False)
    filesystem_store = AtomicFilesystemArtifactPayloadStore(
        _staged_path(layout, staging, layout.cas_root)
    )
    IndexService(_staged_path(layout, staging, layout.index_root))
    database_path = _staged_path(layout, staging, layout.database_path)
    database = DuckDBExecutionStore(database_path)
    database.close()
    legacy_jobs_path = _staged_path(layout, staging, layout.job_store_path)
    with sqlite3.connect(legacy_jobs_path) as legacy_jobs:
        legacy_jobs.execute(
            """
            CREATE TABLE runtime_jobs (
                job_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                cancel_requested INTEGER NOT NULL,
                attempt_count INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                deadline_at TEXT,
                timeout_seconds REAL,
                result_json TEXT,
                error_type TEXT,
                error_message TEXT
            )
            """
        )
    handler: DurableJobHandler = _NoopDurableJobHandler()
    handlers = dict.fromkeys(JobKind, handler)
    payload_store = AuthoritativeArtifactPayloadStore(
        payload_store=filesystem_store,
        database_path=database_path,
    )
    with DurableJobManager(
        database_path,
        handlers=handlers,
        payload_store=payload_store,
        legacy_database_path=legacy_jobs_path,
        max_workers=1,
    ):
        pass
    workspace_id = _workspace_identity(configuration, layout, model_lock_id)
    ledger = _migration_ledger(workspace_id=workspace_id, migrations=[])
    ledger_path = _staged_path(layout, staging, layout.migration_ledger_path)
    with ledger_path.open("xb") as stream:
        stream.write(canonical_json_bytes(ledger))
        stream.flush()
        os.fsync(stream.fileno())
    manifest = _manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
    )
    manifest_path = _staged_path(layout, staging, layout.manifest_path)
    with manifest_path.open("xb") as stream:
        stream.write(canonical_json_bytes(manifest))
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(staging)
    return manifest


def _validate_existing(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
) -> WorkspaceInitializationResult:
    if not layout.root.exists():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.NOT_INITIALIZED,
            "workspace has not been initialized",
            "run bijux-canon-runtime init with this workspace and locked model",
        )
    if not layout.root.is_dir() or layout.root.is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace root is not a real directory",
            "select a non-symlink directory path",
        )
    if not layout.manifest_path.is_file() or layout.manifest_path.is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace exists without a valid manifest",
            "restore a backup or move the partial directory aside before retrying",
        )
    manifest = _load_manifest(layout.manifest_path)
    recorded_version = manifest.get("workspace_version")
    if recorded_version != layout.workspace_version:
        direction = (
            "newer than this Runtime"
            if isinstance(recorded_version, int)
            and recorded_version > layout.workspace_version
            else "older than the supported migration floor"
        )
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_VERSION,
            f"workspace version is {direction}",
            "use a compatible Runtime release; never downgrade in place, and restore "
            "the recorded migration backup to roll back",
        )
    expected_keys = {
        "configuration",
        "configuration_identity_sha256",
        "created_at",
        "layout",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
        "workspace_version",
    }
    if set(manifest) != expected_keys or not isinstance(
        manifest.get("created_at"), str
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest fields are invalid",
            "restore a verified backup or select another workspace",
        )
    workspace_id = manifest.get("workspace_id")
    if not isinstance(workspace_id, str):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest identity is invalid",
            "restore a verified backup or select another workspace",
        )
    if (
        not layout.migration_ledger_path.is_file()
        or layout.migration_ledger_path.is_symlink()
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace migration ledger is missing",
            "restore the workspace manifest and migration ledger from one backup",
        )
    ledger = _load_migration_ledger(
        layout.migration_ledger_path,
        workspace_id=workspace_id,
    )
    _validate_migration_backups(layout, ledger)
    expected = _manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(manifest["created_at"]),
    )
    _raise_location_mismatch(
        _layout_location_mismatches(manifest.get("layout"), expected["layout"])
    )
    configuration_mismatches = _configuration_authority_mismatches(
        manifest.get("configuration"),
        expected["configuration"],
    )
    if configuration_mismatches:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "workspace effective configuration differs: "
            + ", ".join(configuration_mismatches),
            "use the recorded value for each named field or initialize another "
            "workspace",
        )
    if _configuration_authority_record(
        manifest.get("configuration")
    ) != _configuration_authority_record(expected["configuration"]):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "workspace effective configuration differs",
            "use the original effective settings or initialize another workspace",
        )
    compatible_fields = (
        "configuration_identity_sha256",
        "layout_identity_sha256",
        "migration_ledger_sha256",
        "model_lock_artifact_id",
        "schema_version",
        "workspace_id",
    )
    mismatches = [
        field for field in compatible_fields if manifest.get(field) != expected[field]
    ]
    if mismatches:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_CONFIGURATION,
            "workspace configuration differs: " + ", ".join(mismatches),
            "use the original configuration or initialize another workspace",
        )
    _validate_workspace_state_paths(layout)
    return _result(manifest, layout, WorkspaceInitializationStatus.UNCHANGED)


def _validate_state_stores(layout: RuntimeWorkspaceLayout) -> None:
    try:
        database = DuckDBExecutionStore(layout.database_path, read_only=True)
        try:
            database.validate_schema()
        finally:
            database.close()
        with sqlite3.connect(
            f"{layout.job_store_path.as_uri()}?mode=ro",
            uri=True,
        ) as jobs:
            if jobs.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise RuntimeError("durable job database integrity check failed")
            jobs.execute(
                """
                SELECT job_id, kind, idempotency_key, request_sha256,
                       payload_json, status, cancel_requested, attempt_count,
                       submitted_at, started_at, finished_at, deadline_at,
                       timeout_seconds, result_json, error_type, error_message
                FROM runtime_jobs LIMIT 0
                """
            )
    except Exception as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_STATE,
            "workspace state database schema or integrity is invalid",
            "restore the whole workspace from a verified compatible backup",
        ) from exc


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _write_durable(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _migration_state_identities(layout: RuntimeWorkspaceLayout) -> dict[str, str]:
    paths = [
        layout.manifest_path,
        layout.database_path,
        layout.job_store_path,
    ]
    if layout.migration_ledger_path.is_file():
        paths.append(layout.migration_ledger_path)
    if layout.active_generation_path.is_file():
        paths.append(layout.active_generation_path)
    return {
        path.relative_to(layout.root).as_posix(): _hash_file(path) for path in paths
    }


def _migration_source_state_matches(
    layout: RuntimeWorkspaceLayout,
    backup_path: Path,
    backup: Mapping[str, object],
) -> bool:
    identities = backup.get("state_sha256")
    if not isinstance(identities, dict):
        return False
    for relative_name, expected_identity in identities.items():
        if not isinstance(relative_name, str) or not isinstance(expected_identity, str):
            return False
        if (
            relative_name
            == layout.migration_ledger_path.relative_to(layout.root).as_posix()
        ):
            candidate = backup_path / "workspace-migrations.json"
        else:
            candidate = layout.root / relative_name
        if not candidate.is_file() or _hash_file(candidate) != expected_identity:
            return False
    return True


def _ensure_v1_migration_backup(
    layout: RuntimeWorkspaceLayout,
    source_manifest: bytes,
) -> tuple[Path, dict[str, object]]:
    source_manifest_sha256 = _content_sha256(source_manifest)
    backup_id = "workspace-v1-" + source_manifest_sha256.removeprefix("sha256:")[:16]
    migration_root = layout.backup_root / "workspace-migrations"
    if migration_root.exists() and (
        migration_root.is_symlink() or not migration_root.is_dir()
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration backup root is not a real directory",
            "restore a real backup directory beneath the workspace backup root",
        )
    generation = migration_root / "generations" / backup_id
    if generation.exists():
        if generation.is_symlink() or not generation.is_dir():
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.UNSAFE_PATH,
                "workspace migration backup generation is not a real directory",
                "restore a real backup beneath the workspace backup root",
            )
        try:
            backup = _load_manifest(generation / "backup.json")
            existing_unsigned = dict(backup)
            backup_sha256 = existing_unsigned.pop("backup_manifest_sha256", None)
            if (
                set(backup)
                != {
                    "backup_id",
                    "backup_manifest_sha256",
                    "created_at",
                    "migration_id",
                    "schema_version",
                    "source_manifest_sha256",
                    "state_sha256",
                }
                or backup.get("backup_id") != backup_id
                or backup.get("schema_version")
                != "bijux.runtime.workspace-migration-backup.v1"
                or backup_sha256 != _record_identity(existing_unsigned)
                or backup.get("migration_id") != _V1_TO_V2_MIGRATION_ID
                or backup.get("source_manifest_sha256") != source_manifest_sha256
                or (generation / "workspace.json").read_bytes() != source_manifest
                or not _migration_source_state_matches(layout, generation, backup)
            ):
                raise ValueError
            return generation, backup
        except (OSError, ValueError, WorkspaceInitializationError) as exc:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_STATE,
                "existing workspace migration backup is invalid",
                "preserve the workspace and restore a verified migration backup",
            ) from exc
    staging_root = migration_root / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    if staging_root.is_symlink() or not staging_root.is_dir():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration staging root is not a real directory",
            "restore a real staging directory beneath the workspace backup root",
        )
    staging = Path(
        tempfile.mkdtemp(prefix=f"{backup_id}.", suffix=".building", dir=staging_root)
    )
    try:
        _write_durable(staging / "workspace.json", source_manifest)
        new_unsigned: dict[str, object] = {
            "backup_id": backup_id,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "migration_id": _V1_TO_V2_MIGRATION_ID,
            "schema_version": "bijux.runtime.workspace-migration-backup.v1",
            "source_manifest_sha256": source_manifest_sha256,
            "state_sha256": _migration_state_identities(layout),
        }
        backup = {
            **new_unsigned,
            "backup_manifest_sha256": _record_identity(new_unsigned),
        }
        _write_durable(staging / "backup.json", canonical_json_bytes(backup))
        _fsync_directory(staging)
        generation.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, generation)
        _fsync_directory(generation.parent)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return generation, backup


def _ensure_v2_migration_backup(
    layout: RuntimeWorkspaceLayout,
    source_manifest: bytes,
    source_ledger: bytes,
) -> tuple[Path, dict[str, object]]:
    source_manifest_sha256 = _content_sha256(source_manifest)
    source_ledger_sha256 = _content_sha256(source_ledger)
    backup_id = "workspace-v2-" + source_manifest_sha256.removeprefix("sha256:")[:16]
    migration_root = layout.backup_root / "workspace-migrations"
    if migration_root.exists() and (
        migration_root.is_symlink() or not migration_root.is_dir()
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration backup root is not a real directory",
            "restore a real backup directory beneath the workspace backup root",
        )
    generation = migration_root / "generations" / backup_id
    if generation.exists():
        if generation.is_symlink() or not generation.is_dir():
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.UNSAFE_PATH,
                "workspace migration backup generation is not a real directory",
                "restore a real backup beneath the workspace backup root",
            )
        try:
            backup = _load_manifest(generation / "backup.json")
            existing_unsigned = dict(backup)
            backup_sha256 = existing_unsigned.pop("backup_manifest_sha256", None)
            if (
                set(backup)
                != {
                    "backup_id",
                    "backup_manifest_sha256",
                    "created_at",
                    "migration_id",
                    "schema_version",
                    "source_manifest_sha256",
                    "source_migration_ledger_sha256",
                    "state_sha256",
                }
                or backup.get("backup_id") != backup_id
                or backup.get("schema_version")
                != "bijux.runtime.workspace-migration-backup.v2"
                or backup_sha256 != _record_identity(existing_unsigned)
                or backup.get("migration_id") != _V2_TO_V3_MIGRATION_ID
                or backup.get("source_manifest_sha256") != source_manifest_sha256
                or backup.get("source_migration_ledger_sha256") != source_ledger_sha256
                or (generation / "workspace.json").read_bytes() != source_manifest
                or (generation / "workspace-migrations.json").read_bytes()
                != source_ledger
                or not _migration_source_state_matches(layout, generation, backup)
            ):
                raise ValueError
            return generation, backup
        except (OSError, ValueError, WorkspaceInitializationError) as exc:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_STATE,
                "existing workspace migration backup is invalid",
                "preserve the workspace and restore a verified migration backup",
            ) from exc
    staging_root = migration_root / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    if staging_root.is_symlink() or not staging_root.is_dir():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration staging root is not a real directory",
            "restore a real staging directory beneath the workspace backup root",
        )
    staging = Path(
        tempfile.mkdtemp(prefix=f"{backup_id}.", suffix=".building", dir=staging_root)
    )
    try:
        _write_durable(staging / "workspace.json", source_manifest)
        _write_durable(staging / "workspace-migrations.json", source_ledger)
        new_unsigned: dict[str, object] = {
            "backup_id": backup_id,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "migration_id": _V2_TO_V3_MIGRATION_ID,
            "schema_version": "bijux.runtime.workspace-migration-backup.v2",
            "source_manifest_sha256": source_manifest_sha256,
            "source_migration_ledger_sha256": source_ledger_sha256,
            "state_sha256": _migration_state_identities(layout),
        }
        backup = {
            **new_unsigned,
            "backup_manifest_sha256": _record_identity(new_unsigned),
        }
        _write_durable(staging / "backup.json", canonical_json_bytes(backup))
        _fsync_directory(staging)
        generation.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, generation)
        _fsync_directory(generation.parent)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return generation, backup


def _ensure_versioned_migration_backup(
    layout: RuntimeWorkspaceLayout,
    source_manifest: bytes,
    source_ledger: bytes,
    *,
    source_version: int,
    migration_id: str,
) -> tuple[Path, dict[str, object]]:
    source_manifest_sha256 = _content_sha256(source_manifest)
    source_ledger_sha256 = _content_sha256(source_ledger)
    backup_id = (
        f"workspace-v{source_version}-"
        + source_manifest_sha256.removeprefix("sha256:")[:16]
    )
    migration_root = layout.backup_root / "workspace-migrations"
    if migration_root.exists() and (
        migration_root.is_symlink() or not migration_root.is_dir()
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration backup root is not a real directory",
            "restore a real backup directory beneath the workspace backup root",
        )
    generation = migration_root / "generations" / backup_id
    if generation.exists():
        if generation.is_symlink() or not generation.is_dir():
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.UNSAFE_PATH,
                "workspace migration backup generation is not a real directory",
                "restore a real backup beneath the workspace backup root",
            )
        try:
            backup = _load_manifest(generation / "backup.json")
            unsigned = dict(backup)
            backup_sha256 = unsigned.pop("backup_manifest_sha256", None)
            if (
                set(backup)
                != {
                    "backup_id",
                    "backup_manifest_sha256",
                    "created_at",
                    "migration_id",
                    "schema_version",
                    "source_manifest_sha256",
                    "source_migration_ledger_sha256",
                    "state_sha256",
                }
                or backup.get("backup_id") != backup_id
                or backup.get("schema_version")
                != "bijux.runtime.workspace-migration-backup.v2"
                or backup_sha256 != _record_identity(unsigned)
                or backup.get("migration_id") != migration_id
                or backup.get("source_manifest_sha256") != source_manifest_sha256
                or backup.get("source_migration_ledger_sha256") != source_ledger_sha256
                or (generation / "workspace.json").read_bytes() != source_manifest
                or (generation / "workspace-migrations.json").read_bytes()
                != source_ledger
                or not _migration_source_state_matches(layout, generation, backup)
            ):
                raise ValueError
            return generation, backup
        except (OSError, ValueError, WorkspaceInitializationError) as exc:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_STATE,
                "existing workspace migration backup is invalid",
                "preserve the workspace and restore a verified migration backup",
            ) from exc
    staging_root = migration_root / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    if staging_root.is_symlink() or not staging_root.is_dir():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace migration staging root is not a real directory",
            "restore a real staging directory beneath the workspace backup root",
        )
    staging = Path(
        tempfile.mkdtemp(prefix=f"{backup_id}.", suffix=".building", dir=staging_root)
    )
    try:
        _write_durable(staging / "workspace.json", source_manifest)
        _write_durable(staging / "workspace-migrations.json", source_ledger)
        backup_unsigned: dict[str, object] = {
            "backup_id": backup_id,
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "migration_id": migration_id,
            "schema_version": "bijux.runtime.workspace-migration-backup.v2",
            "source_manifest_sha256": source_manifest_sha256,
            "source_migration_ledger_sha256": source_ledger_sha256,
            "state_sha256": _migration_state_identities(layout),
        }
        backup = {
            **backup_unsigned,
            "backup_manifest_sha256": _record_identity(backup_unsigned),
        }
        _write_durable(staging / "backup.json", canonical_json_bytes(backup))
        _fsync_directory(staging)
        generation.parent.mkdir(parents=True, exist_ok=True)
        os.rename(staging, generation)
        _fsync_directory(generation.parent)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return generation, backup


def _ensure_v3_migration_backup(
    layout: RuntimeWorkspaceLayout,
    source_manifest: bytes,
    source_ledger: bytes,
) -> tuple[Path, dict[str, object]]:
    return _ensure_versioned_migration_backup(
        layout,
        source_manifest,
        source_ledger,
        source_version=3,
        migration_id=_V3_TO_V4_MIGRATION_ID,
    )


def _ensure_v4_migration_backup(
    layout: RuntimeWorkspaceLayout,
    source_manifest: bytes,
    source_ledger: bytes,
) -> tuple[Path, dict[str, object]]:
    return _ensure_versioned_migration_backup(
        layout,
        source_manifest,
        source_ledger,
        source_version=4,
        migration_id=_V4_TO_V5_MIGRATION_ID,
    )


def _migrate_workspace_v2_to_v3(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    target_layout = _legacy_v3_layout_record(layout)
    target_configuration = _configuration_record_for_layout(
        configuration,
        target_layout,
        retrieval_policy_id=configuration.retrieval_policy_id,
    )
    target_workspace_id = _workspace_id_for_version(
        configuration_identity_sha256=str(target_configuration["identity_sha256"]),
        layout_identity_sha256=str(target_layout["identity_sha256"]),
        model_lock_id=model_lock_id,
        workspace_version=3,
    )
    source_ledger_path = layout.migration_ledger_path
    try:
        source_ledger = _validate_legacy_v2(
            configuration,
            layout,
            model_lock_id,
            source_manifest,
        )
    except WorkspaceInitializationError as source_error:
        try:
            interrupted_ledger = _load_migration_ledger(
                layout.migration_ledger_path,
                workspace_id=target_workspace_id,
            )
            _validate_migration_backups(layout, interrupted_ledger)
            migrations = interrupted_ledger["migrations"]
            if not isinstance(migrations, list) or not migrations:
                raise ValueError
            latest = migrations[-1]
            if (
                not isinstance(latest, dict)
                or latest.get("migration_id") != _V2_TO_V3_MIGRATION_ID
                or latest.get("source_manifest_sha256")
                != _content_sha256(canonical_json_bytes(source_manifest))
            ):
                raise ValueError
            source_ledger_path = (
                layout.root / str(latest["backup_manifest_path"])
            ).parent / "workspace-migrations.json"
            source_ledger = _validate_legacy_v2(
                configuration,
                layout,
                model_lock_id,
                source_manifest,
                ledger_path=source_ledger_path,
            )
        except (OSError, ValueError, WorkspaceInitializationError) as error:
            raise source_error from error
    source_content = canonical_json_bytes(source_manifest)
    source_ledger_content = canonical_json_bytes(source_ledger)
    source_manifest_sha256 = _content_sha256(source_content)
    backup_path, backup = _ensure_v2_migration_backup(
        layout,
        source_content,
        source_ledger_content,
    )
    backup_manifest_path = (
        (backup_path / "backup.json").relative_to(layout.root).as_posix()
    )
    source_migrations = source_ledger["migrations"]
    assert isinstance(source_migrations, list)
    migration = {
        "applied_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "backup_manifest_path": backup_manifest_path,
        "backup_manifest_sha256": backup["backup_manifest_sha256"],
        "from_version": 2,
        "migration_id": _V2_TO_V3_MIGRATION_ID,
        "source_manifest_sha256": source_manifest_sha256,
        "to_version": 3,
    }
    ledger = _migration_ledger(
        workspace_id=target_workspace_id,
        migrations=[*source_migrations, migration],
    )
    if layout.migration_ledger_path != source_ledger_path:
        interrupted = _load_migration_ledger(
            layout.migration_ledger_path,
            workspace_id=target_workspace_id,
        )
        interrupted_migrations = interrupted["migrations"]
        if (
            not isinstance(interrupted_migrations, list)
            or len(interrupted_migrations) != len(source_migrations) + 1
        ):
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "interrupted version-3 migration ledger is invalid",
                "restore workspace authority from the recorded migration backup",
            )
        migration = interrupted_migrations[-1]
        if not isinstance(migration, dict):
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "interrupted version-3 migration record is invalid",
                "restore workspace authority from the recorded migration backup",
            )
        ledger = interrupted
    target_manifest = _legacy_v3_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(source_manifest["created_at"]),
    )
    if not _migration_source_state_matches(layout, backup_path, backup):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace state changed after migration backup preflight",
            "stop every Runtime writer and retry from the unchanged workspace",
        )
    staging = Path(
        tempfile.mkdtemp(
            prefix="workspace-v2-v3.",
            suffix=".migrating",
            dir=layout.staging_root,
        )
    )
    try:
        staged_ledger = staging / "workspace-migrations.json"
        staged_manifest = staging / "workspace.json"
        _write_durable(staged_ledger, canonical_json_bytes(ledger))
        _write_durable(staged_manifest, canonical_json_bytes(target_manifest))
        _fsync_directory(staging)
        os.replace(staged_ledger, layout.migration_ledger_path)
        _fsync_directory(layout.root)
        os.replace(staged_manifest, layout.manifest_path)
        _fsync_directory(layout.root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _validate_legacy_v3(configuration, layout, model_lock_id, target_manifest)
    return _result(
        target_manifest,
        layout,
        WorkspaceInitializationStatus.MIGRATED,
        applied_migration_ids=(_V2_TO_V3_MIGRATION_ID,),
        rollback_backup_path=str(backup_path),
    )


def _migrate_workspace_v2_to_v4(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    migrated_v3 = _migrate_workspace_v2_to_v3(
        configuration,
        layout,
        model_lock_id,
        source_manifest,
    )
    migrated_v4 = _migrate_workspace_v3_to_v4(
        configuration,
        layout,
        model_lock_id,
        _load_manifest(layout.manifest_path),
    )
    return WorkspaceInitializationResult(
        configuration_identity_sha256=(migrated_v4.configuration_identity_sha256),
        layout_identity_sha256=migrated_v4.layout_identity_sha256,
        model_lock_artifact_id=migrated_v4.model_lock_artifact_id,
        status=WorkspaceInitializationStatus.MIGRATED,
        workspace_id=migrated_v4.workspace_id,
        workspace_root=migrated_v4.workspace_root,
        workspace_version=migrated_v4.workspace_version,
        applied_migration_ids=(
            *migrated_v3.applied_migration_ids,
            *migrated_v4.applied_migration_ids,
        ),
        rollback_backup_path=migrated_v3.rollback_backup_path,
    )


def _migrate_workspace_v3_to_v4(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    target_layout = _legacy_v4_layout_record(layout)
    target_configuration = _configuration_record_for_layout(
        configuration,
        target_layout,
        retrieval_policy_id=configuration.retrieval_policy_id,
    )
    target_workspace_id = _workspace_id_for_version(
        configuration_identity_sha256=str(target_configuration["identity_sha256"]),
        layout_identity_sha256=str(target_layout["identity_sha256"]),
        model_lock_id=model_lock_id,
        workspace_version=4,
    )
    source_ledger_path = layout.migration_ledger_path
    try:
        source_ledger = _validate_legacy_v3(
            configuration,
            layout,
            model_lock_id,
            source_manifest,
        )
    except WorkspaceInitializationError as source_error:
        try:
            interrupted = _load_migration_ledger(
                layout.migration_ledger_path,
                workspace_id=target_workspace_id,
            )
            _validate_migration_backups(layout, interrupted)
            migrations = interrupted["migrations"]
            if not isinstance(migrations, list) or not migrations:
                raise ValueError
            latest = migrations[-1]
            if (
                not isinstance(latest, dict)
                or latest.get("migration_id") != _V3_TO_V4_MIGRATION_ID
                or latest.get("source_manifest_sha256")
                != _content_sha256(canonical_json_bytes(source_manifest))
            ):
                raise ValueError
            source_ledger_path = (
                layout.root / str(latest["backup_manifest_path"])
            ).parent / "workspace-migrations.json"
            source_ledger = _validate_legacy_v3(
                configuration,
                layout,
                model_lock_id,
                source_manifest,
                ledger_path=source_ledger_path,
            )
        except (OSError, ValueError, WorkspaceInitializationError) as error:
            raise source_error from error
    source_content = canonical_json_bytes(source_manifest)
    source_ledger_content = canonical_json_bytes(source_ledger)
    source_manifest_sha256 = _content_sha256(source_content)
    backup_path, backup = _ensure_v3_migration_backup(
        layout,
        source_content,
        source_ledger_content,
    )
    backup_manifest_path = (
        (backup_path / "backup.json").relative_to(layout.root).as_posix()
    )
    source_migrations = source_ledger["migrations"]
    assert isinstance(source_migrations, list)
    migration = {
        "applied_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "backup_manifest_path": backup_manifest_path,
        "backup_manifest_sha256": backup["backup_manifest_sha256"],
        "from_version": 3,
        "migration_id": _V3_TO_V4_MIGRATION_ID,
        "source_manifest_sha256": source_manifest_sha256,
        "to_version": 4,
    }
    ledger = _migration_ledger(
        workspace_id=target_workspace_id,
        migrations=[*source_migrations, migration],
    )
    if layout.migration_ledger_path != source_ledger_path:
        ledger = _load_migration_ledger(
            layout.migration_ledger_path,
            workspace_id=target_workspace_id,
        )
    target_manifest = _legacy_v4_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(source_manifest["created_at"]),
    )
    if not _migration_source_state_matches(layout, backup_path, backup):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace state changed after migration backup preflight",
            "stop every Runtime writer and retry from the unchanged workspace",
        )
    staging = Path(
        tempfile.mkdtemp(
            prefix="workspace-v3-v4.",
            suffix=".migrating",
            dir=layout.staging_root,
        )
    )
    try:
        staged_ledger = staging / "workspace-migrations.json"
        staged_manifest = staging / "workspace.json"
        _write_durable(staged_ledger, canonical_json_bytes(ledger))
        _write_durable(staged_manifest, canonical_json_bytes(target_manifest))
        _fsync_directory(staging)
        os.replace(staged_ledger, layout.migration_ledger_path)
        _fsync_directory(layout.root)
        os.replace(staged_manifest, layout.manifest_path)
        _fsync_directory(layout.root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _validate_legacy_v4(configuration, layout, model_lock_id, target_manifest)
    return _result(
        target_manifest,
        layout,
        WorkspaceInitializationStatus.MIGRATED,
        applied_migration_ids=(_V3_TO_V4_MIGRATION_ID,),
        rollback_backup_path=str(backup_path),
    )


def _migrate_workspace_v4_to_v5(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    target_workspace_id = _workspace_identity(configuration, layout, model_lock_id)
    source_ledger_path = layout.migration_ledger_path
    try:
        source_ledger = _validate_legacy_v4(
            configuration,
            layout,
            model_lock_id,
            source_manifest,
        )
    except WorkspaceInitializationError as source_error:
        try:
            interrupted = _load_migration_ledger(
                layout.migration_ledger_path,
                workspace_id=target_workspace_id,
            )
            _validate_migration_backups(layout, interrupted)
            migrations = interrupted["migrations"]
            if not isinstance(migrations, list) or not migrations:
                raise ValueError
            latest = migrations[-1]
            if (
                not isinstance(latest, dict)
                or latest.get("migration_id") != _V4_TO_V5_MIGRATION_ID
                or latest.get("source_manifest_sha256")
                != _content_sha256(canonical_json_bytes(source_manifest))
            ):
                raise ValueError
            source_ledger_path = (
                layout.root / str(latest["backup_manifest_path"])
            ).parent / "workspace-migrations.json"
            source_ledger = _validate_legacy_v4(
                configuration,
                layout,
                model_lock_id,
                source_manifest,
                ledger_path=source_ledger_path,
            )
        except (OSError, ValueError, WorkspaceInitializationError) as error:
            raise source_error from error
    source_content = canonical_json_bytes(source_manifest)
    source_ledger_content = canonical_json_bytes(source_ledger)
    source_manifest_sha256 = _content_sha256(source_content)
    backup_path, backup = _ensure_v4_migration_backup(
        layout,
        source_content,
        source_ledger_content,
    )
    backup_manifest_path = (
        (backup_path / "backup.json").relative_to(layout.root).as_posix()
    )
    source_migrations = source_ledger["migrations"]
    assert isinstance(source_migrations, list)
    migration = {
        "applied_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "backup_manifest_path": backup_manifest_path,
        "backup_manifest_sha256": backup["backup_manifest_sha256"],
        "from_version": 4,
        "migration_id": _V4_TO_V5_MIGRATION_ID,
        "source_manifest_sha256": source_manifest_sha256,
        "to_version": 5,
    }
    ledger = _migration_ledger(
        workspace_id=target_workspace_id,
        migrations=[*source_migrations, migration],
    )
    if layout.migration_ledger_path != source_ledger_path:
        ledger = _load_migration_ledger(
            layout.migration_ledger_path,
            workspace_id=target_workspace_id,
        )
    target_manifest = _manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(source_manifest["created_at"]),
    )
    if not _migration_source_state_matches(layout, backup_path, backup):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace state changed after migration backup preflight",
            "stop every Runtime writer and retry from the unchanged workspace",
        )
    staging = Path(
        tempfile.mkdtemp(
            prefix="workspace-v4-v5.",
            suffix=".migrating",
            dir=layout.staging_root,
        )
    )
    try:
        staged_ledger = staging / "workspace-migrations.json"
        staged_manifest = staging / "workspace.json"
        _write_durable(staged_ledger, canonical_json_bytes(ledger))
        _write_durable(staged_manifest, canonical_json_bytes(target_manifest))
        _fsync_directory(staging)
        os.replace(staged_ledger, layout.migration_ledger_path)
        _fsync_directory(layout.root)
        os.replace(staged_manifest, layout.manifest_path)
        _fsync_directory(layout.root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _validate_existing(configuration, layout, model_lock_id)
    return _result(
        target_manifest,
        layout,
        WorkspaceInitializationStatus.MIGRATED,
        applied_migration_ids=(_V4_TO_V5_MIGRATION_ID,),
        rollback_backup_path=str(backup_path),
    )


def _migrate_workspace_v2_to_v5(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    migrated_v4 = _migrate_workspace_v2_to_v4(
        configuration,
        layout,
        model_lock_id,
        source_manifest,
    )
    migrated_v5 = _migrate_workspace_v4_to_v5(
        configuration,
        layout,
        model_lock_id,
        _load_manifest(layout.manifest_path),
    )
    return WorkspaceInitializationResult(
        configuration_identity_sha256=migrated_v5.configuration_identity_sha256,
        layout_identity_sha256=migrated_v5.layout_identity_sha256,
        model_lock_artifact_id=migrated_v5.model_lock_artifact_id,
        status=WorkspaceInitializationStatus.MIGRATED,
        workspace_id=migrated_v5.workspace_id,
        workspace_root=migrated_v5.workspace_root,
        workspace_version=migrated_v5.workspace_version,
        applied_migration_ids=(
            *migrated_v4.applied_migration_ids,
            *migrated_v5.applied_migration_ids,
        ),
        rollback_backup_path=migrated_v4.rollback_backup_path,
    )


def _migrate_workspace_v3_to_v5(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    migrated_v4 = _migrate_workspace_v3_to_v4(
        configuration,
        layout,
        model_lock_id,
        source_manifest,
    )
    migrated_v5 = _migrate_workspace_v4_to_v5(
        configuration,
        layout,
        model_lock_id,
        _load_manifest(layout.manifest_path),
    )
    return WorkspaceInitializationResult(
        configuration_identity_sha256=migrated_v5.configuration_identity_sha256,
        layout_identity_sha256=migrated_v5.layout_identity_sha256,
        model_lock_artifact_id=migrated_v5.model_lock_artifact_id,
        status=WorkspaceInitializationStatus.MIGRATED,
        workspace_id=migrated_v5.workspace_id,
        workspace_root=migrated_v5.workspace_root,
        workspace_version=migrated_v5.workspace_version,
        applied_migration_ids=(
            *migrated_v4.applied_migration_ids,
            *migrated_v5.applied_migration_ids,
        ),
        rollback_backup_path=migrated_v4.rollback_backup_path,
    )


def _migrate_workspace_v1_to_v5(
    configuration: RuntimeConfiguration,
    layout: RuntimeWorkspaceLayout,
    model_lock_id: str,
    source_manifest: dict[str, object],
) -> WorkspaceInitializationResult:
    _validate_legacy_v1(
        configuration,
        layout,
        model_lock_id,
        source_manifest,
    )
    source_content = canonical_json_bytes(source_manifest)
    source_manifest_sha256 = _content_sha256(source_content)
    backup_path, backup = _ensure_v1_migration_backup(layout, source_content)
    legacy_v2_layout = _legacy_v2_layout_record(layout)
    legacy_v2_configuration = _legacy_v2_configuration_record(
        configuration,
        legacy_v2_layout,
    )
    target_workspace_id = _workspace_id_for_version(
        configuration_identity_sha256=str(legacy_v2_configuration["identity_sha256"]),
        layout_identity_sha256=str(legacy_v2_layout["identity_sha256"]),
        model_lock_id=model_lock_id,
        workspace_version=2,
    )
    backup_manifest_path = (
        (backup_path / "backup.json").relative_to(layout.root).as_posix()
    )
    existing_ledger = None
    if layout.migration_ledger_path.is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "interrupted workspace migration ledger is a symbolic link",
            "restore the ledger as a real workspace-owned file",
        )
    if layout.migration_ledger_path.exists():
        existing_ledger = _load_migration_ledger(
            layout.migration_ledger_path,
            workspace_id=target_workspace_id,
        )
    if existing_ledger is None:
        migration = {
            "applied_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "backup_manifest_path": backup_manifest_path,
            "backup_manifest_sha256": backup["backup_manifest_sha256"],
            "from_version": 1,
            "migration_id": _V1_TO_V2_MIGRATION_ID,
            "source_manifest_sha256": source_manifest_sha256,
            "to_version": 2,
        }
        ledger = _migration_ledger(
            workspace_id=target_workspace_id,
            migrations=[migration],
        )
    else:
        migrations = existing_ledger["migrations"]
        if not isinstance(migrations, list) or len(migrations) != 1:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "interrupted workspace migration ledger is invalid",
                "restore workspace.json from the recorded migration backup",
            )
        migration = migrations[0]
        if (
            not isinstance(migration, dict)
            or migration.get("source_manifest_sha256") != source_manifest_sha256
            or migration.get("backup_manifest_path") != backup_manifest_path
            or migration.get("backup_manifest_sha256")
            != backup["backup_manifest_sha256"]
        ):
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "interrupted workspace migration does not match its source backup",
                "restore workspace.json and workspace-migrations.json from one backup",
            )
        ledger = existing_ledger
    target_manifest = _legacy_v2_manifest_record(
        configuration,
        layout,
        model_lock_id,
        str(ledger["ledger_sha256"]),
        created_at=str(source_manifest["created_at"]),
    )
    if not _migration_source_state_matches(layout, backup_path, backup):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.WORKSPACE_BUSY,
            "workspace state changed after migration backup preflight",
            "stop every Runtime writer and retry from the unchanged version-1 manifest",
        )
    staging = Path(
        tempfile.mkdtemp(
            prefix="workspace-v1-v2.",
            suffix=".migrating",
            dir=layout.staging_root,
        )
    )
    try:
        staged_ledger = staging / "workspace-migrations.json"
        staged_manifest = staging / "workspace.json"
        _write_durable(staged_ledger, canonical_json_bytes(ledger))
        _write_durable(staged_manifest, canonical_json_bytes(target_manifest))
        _fsync_directory(staging)
        os.replace(staged_ledger, layout.migration_ledger_path)
        _fsync_directory(layout.root)
        os.replace(staged_manifest, layout.manifest_path)
        _fsync_directory(layout.root)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    migrated = _migrate_workspace_v2_to_v5(
        configuration,
        layout,
        model_lock_id,
        target_manifest,
    )
    return WorkspaceInitializationResult(
        configuration_identity_sha256=migrated.configuration_identity_sha256,
        layout_identity_sha256=migrated.layout_identity_sha256,
        model_lock_artifact_id=migrated.model_lock_artifact_id,
        status=WorkspaceInitializationStatus.MIGRATED,
        workspace_id=migrated.workspace_id,
        workspace_root=migrated.workspace_root,
        workspace_version=migrated.workspace_version,
        applied_migration_ids=(
            _V1_TO_V2_MIGRATION_ID,
            _V2_TO_V3_MIGRATION_ID,
            _V3_TO_V4_MIGRATION_ID,
            _V4_TO_V5_MIGRATION_ID,
        ),
        rollback_backup_path=str(backup_path),
    )


@contextmanager
def _initialization_lock(layout: RuntimeWorkspaceLayout) -> Iterator[None]:
    lock_path = layout.root.parent / f".{layout.root.name}.initialization.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def initialize_runtime_workspace(
    configuration: RuntimeConfiguration,
) -> WorkspaceInitializationResult:
    """Atomically initialize or validate one exact effective workspace."""
    configured_root = configuration.working_root
    if configured_root is not None and configured_root.expanduser().is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace root must not be a symbolic link",
            "select a non-symlink workspace path",
        )
    layout = configuration.require_workspace_layout()
    _validate_owned_paths(layout)
    if layout.root.is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace root must not be a symbolic link",
            "select a non-symlink workspace path",
        )
    layout.root.parent.mkdir(parents=True, exist_ok=True)
    model_lock_id = _configured_model_lock_id(configuration, layout)
    try:
        with _initialization_lock(layout):
            if layout.root.exists():
                if (
                    layout.manifest_path.is_file()
                    and not layout.manifest_path.is_symlink()
                ):
                    existing_manifest = _load_manifest(layout.manifest_path)
                    if existing_manifest.get("workspace_version") == 1:
                        return _migrate_workspace_v1_to_v5(
                            configuration,
                            layout,
                            model_lock_id,
                            existing_manifest,
                        )
                    if existing_manifest.get("workspace_version") == 2:
                        return _migrate_workspace_v2_to_v5(
                            configuration,
                            layout,
                            model_lock_id,
                            existing_manifest,
                        )
                    if existing_manifest.get("workspace_version") == 3:
                        return _migrate_workspace_v3_to_v5(
                            configuration,
                            layout,
                            model_lock_id,
                            existing_manifest,
                        )
                    if existing_manifest.get("workspace_version") == 4:
                        return _migrate_workspace_v4_to_v5(
                            configuration,
                            layout,
                            model_lock_id,
                            existing_manifest,
                        )
                return _validate_existing(configuration, layout, model_lock_id)
            staging = Path(
                tempfile.mkdtemp(
                    prefix=f".{layout.root.name}.",
                    suffix=".initializing",
                    dir=layout.root.parent,
                )
            )
            try:
                manifest = _initialize_staging(
                    configuration,
                    layout,
                    staging,
                    model_lock_id,
                )
                os.rename(staging, layout.root)
                _fsync_directory(layout.root.parent)
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
    except WorkspaceInitializationError:
        raise
    except PermissionError as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNWRITABLE,
            "workspace parent or state is not writable",
            "choose a writable path or correct its permissions",
        ) from exc
    except OSError as exc:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace initialization could not activate complete state",
            "inspect the parent path and retry after resolving the reported error",
        ) from exc
    return _result(manifest, layout, WorkspaceInitializationStatus.INITIALIZED)


def validate_runtime_workspace(
    configuration: RuntimeConfiguration,
    *,
    verify_model: bool = True,
) -> WorkspaceInitializationResult:
    """Validate an initialized effective workspace without creating or repairing it."""
    configured_root = configuration.working_root
    if configured_root is not None and configured_root.expanduser().is_symlink():
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.UNSAFE_PATH,
            "workspace root must not be a symbolic link",
            "select a non-symlink workspace path",
        )
    layout = configuration.require_workspace_layout()
    _validate_owned_paths(layout)
    if not layout.root.exists():
        return _validate_existing(configuration, layout, "")
    if verify_model:
        model_lock_id = _configured_model_lock_id(configuration, layout)
    else:
        manifest = _load_manifest(layout.manifest_path)
        recorded_model_lock_id = manifest.get("model_lock_artifact_id")
        if not isinstance(recorded_model_lock_id, str) or not recorded_model_lock_id:
            raise WorkspaceInitializationError(
                WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
                "workspace manifest has an invalid model lock identity",
                "restore a verified backup or select another workspace",
            )
        model_lock_id = recorded_model_lock_id
    return _validate_existing(configuration, layout, model_lock_id)


__all__ = [
    "NO_MODEL_LOCK_ARTIFACT_ID",
    "initialize_runtime_workspace",
    "validate_runtime_workspace",
    "WorkspaceInitializationError",
    "WorkspaceInitializationErrorCode",
    "WorkspaceInitializationResult",
    "WorkspaceInitializationStatus",
]
