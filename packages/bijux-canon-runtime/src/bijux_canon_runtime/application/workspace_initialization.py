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

from bijux_canon_index.application import IndexService
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
    DurableJobRequest,
    DurableJobManager,
    JobKind,
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
    PARTIAL_WORKSPACE = "partial_workspace"
    UNSAFE_PATH = "unsafe_path"
    UNWRITABLE = "unwritable"


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
    schema_version: str = "bijux.runtime.workspace-initialization-result.v1"

    def record(self) -> dict[str, object]:
        """Return stable JSON output without secret values."""
        return {
            "configuration_identity_sha256": self.configuration_identity_sha256,
            "layout_identity_sha256": self.layout_identity_sha256,
            "model_lock_artifact_id": self.model_lock_artifact_id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "workspace_id": self.workspace_id,
            "workspace_root": self.workspace_root,
            "workspace_version": self.workspace_version,
        }


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
) -> dict[str, object]:
    return {
        "configuration": configuration.redacted_record(),
        "configuration_identity_sha256": configuration.identity_sha256,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "layout": layout.record(),
        "layout_identity_sha256": layout.identity_sha256,
        "model_lock_artifact_id": model_lock_id,
        "schema_version": "bijux.runtime.workspace.v1",
        "workspace_id": _workspace_identity(configuration, layout, model_lock_id),
        "workspace_version": layout.workspace_version,
    }


def _result(
    manifest: Mapping[str, object],
    layout: RuntimeWorkspaceLayout,
    status: WorkspaceInitializationStatus,
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
    AtomicFilesystemArtifactPayloadStore(_staged_path(layout, staging, layout.cas_root))
    IndexService(_staged_path(layout, staging, layout.index_root))
    database = DuckDBExecutionStore(_staged_path(layout, staging, layout.database_path))
    database.close()
    handler: DurableJobHandler = _NoopDurableJobHandler()
    handlers = {kind: handler for kind in JobKind}
    with DurableJobManager(
        _staged_path(layout, staging, layout.job_store_path),
        handlers=handlers,
        max_workers=1,
    ):
        pass
    manifest = _manifest_record(configuration, layout, model_lock_id)
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
    if set(manifest) != expected_keys or not isinstance(
        manifest.get("created_at"), str
    ):
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.CORRUPT_MANIFEST,
            "workspace manifest fields are invalid",
            "restore a verified backup or select another workspace",
        )
    if manifest.get("workspace_version") != layout.workspace_version:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.INCOMPATIBLE_VERSION,
            "workspace version is unsupported",
            "use a supported migration or compatible Runtime release",
        )
    expected = _manifest_record(configuration, layout, model_lock_id)
    compatible_fields = (
        "configuration",
        "configuration_identity_sha256",
        "layout",
        "layout_identity_sha256",
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
    model_lock_id = _verify_model(layout)
    try:
        with _initialization_lock(layout):
            if layout.root.exists():
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


__all__ = [
    "initialize_runtime_workspace",
    "WorkspaceInitializationError",
    "WorkspaceInitializationErrorCode",
    "WorkspaceInitializationResult",
    "WorkspaceInitializationStatus",
]
