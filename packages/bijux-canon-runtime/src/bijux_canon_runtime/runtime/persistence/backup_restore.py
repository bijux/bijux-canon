# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Consistent backup and verified clean-location restore."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import tempfile
from typing import TYPE_CHECKING

from bijux_canon_runtime.model.artifact import canonical_json_bytes
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
    PayloadCorruptionError,
)
from bijux_canon_runtime.runtime.persistence.reachability import (
    ArtifactReachabilityValidator,
)

if TYPE_CHECKING:
    from bijux_canon_runtime.application.runtime_configuration import (
        RuntimeConfiguration,
    )


class BackupIntegrityError(RuntimeError):
    """Raised when backup or restore identity cannot be proven."""


@dataclass(frozen=True, slots=True)
class RuntimeBackupFile:
    """One checksummed workspace-owned file retained outside DuckDB and CAS."""

    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeBackupManifest:
    """Checksummed identity of one database and reachable blob generation."""

    schema_version: str
    backup_id: str
    created_at: str
    database_sha256: str
    reachability_sha256: str
    artifact_ids: tuple[ArtifactID, ...]
    artifact_payload_sha256: tuple[str, ...]
    workspace_files: tuple[RuntimeBackupFile, ...]
    manifest_sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeRestoreResult:
    """Verified identity and paths for one restored Runtime workspace."""

    backup_id: str
    manifest_sha256: str
    restore_root: str
    database_sha256: str
    artifact_count: int
    schema_version: int
    inspection_ready: bool
    offline_replay_ready: bool


class RuntimeBackupManager:
    """Back up one consistent Runtime database and its reachable CAS closure."""

    def __init__(
        self,
        *,
        configuration: RuntimeConfiguration,
    ) -> None:
        layout = configuration.require_workspace_layout()
        self._layout = layout
        self._database_path = layout.database_path
        self._payload_store = AtomicFilesystemArtifactPayloadStore(layout.cas_root)
        self._backup_root = layout.backup_root

    def create_workspace_backup(
        self,
        *,
        backup_id: str,
        created_at: str,
    ) -> tuple[Path, RuntimeBackupManifest]:
        """Create a backup at the configured workspace backup authority."""
        return self.create_backup(
            backup_id=backup_id,
            destination_root=self._backup_root,
            created_at=created_at,
        )

    def create_backup(
        self,
        *,
        backup_id: str,
        destination_root: Path,
        created_at: str,
    ) -> tuple[Path, RuntimeBackupManifest]:
        """Publish a complete backup generation atomically."""
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", backup_id) is None:
            raise ValueError(
                "backup_id must be 1-128 letters, digits, dots, underscores, or hyphens"
            )
        destination = destination_root.resolve()
        generation = destination / "generations" / backup_id
        if generation.exists():
            manifest = self.load_manifest(generation)
            self._validate_generation(generation, manifest)
            if manifest.schema_version != "bijux.runtime.backup.v2":
                raise BackupIntegrityError(
                    "existing backup identity uses a legacy schema; choose a new "
                    "backup_id for a complete workspace backup"
                )
            return generation, manifest
        staging_root = destination / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        staged = Path(
            tempfile.mkdtemp(
                prefix=f"{backup_id}.", suffix=".partial", dir=staging_root
            )
        )
        try:
            store = DuckDBExecutionStore(self._database_path)
            try:
                active_job_row = store._connection.execute(
                    "SELECT count(*) FROM runtime_jobs "
                    "WHERE status IN ('queued', 'running')"
                ).fetchone()
                if active_job_row is None:
                    raise BackupIntegrityError(
                        "backup could not read the durable job authority"
                    )
                active_jobs = int(active_job_row[0])
                if active_jobs:
                    raise BackupIntegrityError(
                        "backup requires zero queued or running jobs"
                    )
                report = ArtifactReachabilityValidator(
                    database_path=self._database_path,
                    payload_store=self._payload_store,
                ).validate()
                if not report.integrity_ok:
                    raise BackupIntegrityError(
                        "backup requires an integrity-clean reachable set"
                    )
                admitted_artifact_ids = tuple(
                    ArtifactID(row[0])
                    for row in store._connection.execute(
                        "SELECT artifact_id FROM artifact_payloads ORDER BY artifact_id"
                    ).fetchall()
                )
                store._connection.execute("CHECKPOINT")
                shutil.copy2(self._database_path, staged / "runtime.duckdb")
                workspace_files = self._copy_workspace_files(staged)
                backup_cas = AtomicFilesystemArtifactPayloadStore(staged / "cas")
                payload_hashes: list[str] = []
                for artifact_id in admitted_artifact_ids:
                    try:
                        artifact = self._payload_store.load(artifact_id)
                    except (KeyError, PayloadCorruptionError, ValueError) as error:
                        raise BackupIntegrityError(
                            "DuckDB payload metadata points to absent or corrupt CAS content"
                        ) from error
                    backup_cas.put(artifact)
                    if backup_cas.load(artifact_id) != artifact:
                        raise BackupIntegrityError("backup blob verification failed")
                    payload_hashes.append(str(artifact.descriptor.payload_sha256))
            finally:
                store.close()
            unsigned: dict[str, object] = {
                "artifact_ids": [str(item) for item in admitted_artifact_ids],
                "artifact_payload_sha256": payload_hashes,
                "backup_id": backup_id,
                "created_at": created_at,
                "database_sha256": self._hash_file(staged / "runtime.duckdb"),
                "reachability_sha256": report.report_sha256,
                "schema_version": "bijux.runtime.backup.v2",
                "workspace_files": [
                    {
                        "relative_path": item.relative_path,
                        "sha256": item.sha256,
                        "size_bytes": item.size_bytes,
                    }
                    for item in workspace_files
                ],
            }
            manifest_hash = hashlib.sha256(self._canonical_bytes(unsigned)).hexdigest()
            manifest_record = {**unsigned, "manifest_sha256": manifest_hash}
            self._write_durable(
                staged / "manifest.json",
                json.dumps(manifest_record, indent=2, sort_keys=True).encode("utf-8")
                + b"\n",
            )
            generation.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staged, generation)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        return generation, self.load_manifest(generation)

    @classmethod
    def restore(
        cls,
        *,
        backup_generation: Path,
        restore_root: Path,
    ) -> RuntimeRestoreResult:
        """Restore into a new root and verify migrations, blobs, and inspection."""
        backup_generation = backup_generation.resolve()
        restore_root = restore_root.resolve()
        if restore_root.exists():
            raise BackupIntegrityError("restore root must not already exist")
        manifest = cls.load_manifest(backup_generation)
        if manifest.schema_version != "bijux.runtime.backup.v2":
            raise BackupIntegrityError(
                "legacy backup does not contain the workspace control state required "
                "for an inspection-ready restore"
            )
        cls._validate_generation(backup_generation, manifest)
        source_database = backup_generation / "runtime.duckdb"
        if cls._hash_file(source_database) != manifest.database_sha256:
            raise BackupIntegrityError("backup database checksum does not match")
        staged = restore_root.with_name(restore_root.name + ".partial")
        if staged.exists():
            raise BackupIntegrityError("restore staging root already exists")
        staged.mkdir(parents=True)
        try:
            workspace_record = cls._load_workspace_record(
                backup_generation / "workspace" / "workspace.json"
            )
            source_root = cls._recorded_workspace_root(workspace_record)
            retained_paths = {item.relative_path for item in manifest.workspace_files}
            required_paths = {
                cls._recorded_relative_path(
                    workspace_record,
                    field,
                    source_root=source_root,
                ).as_posix()
                for field in (
                    "job_store_path",
                    "manifest_path",
                    "migration_ledger_path",
                )
            }
            if not required_paths.issubset(retained_paths):
                raise BackupIntegrityError(
                    "backup workspace control file inventory is incomplete"
                )
            database_relative = cls._recorded_relative_path(
                workspace_record,
                "database_path",
                source_root=source_root,
            )
            cas_relative = cls._recorded_relative_path(
                workspace_record,
                "cas_root",
                source_root=source_root,
            )
            for item in manifest.workspace_files:
                source = backup_generation / "workspace" / item.relative_path
                destination = staged / item.relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            database_target = staged / database_relative
            database_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_database, database_target)
            source_cas = AtomicFilesystemArtifactPayloadStore(backup_generation / "cas")
            restored_cas = AtomicFilesystemArtifactPayloadStore(staged / cas_relative)
            for artifact_id, payload_hash in zip(
                manifest.artifact_ids,
                manifest.artifact_payload_sha256,
                strict=True,
            ):
                try:
                    artifact = source_cas.load(artifact_id)
                except (KeyError, PayloadCorruptionError, ValueError) as error:
                    raise BackupIntegrityError(
                        "backup artifact content is absent or corrupt"
                    ) from error
                if str(artifact.descriptor.payload_sha256) != payload_hash:
                    raise BackupIntegrityError("backup manifest payload hash mismatch")
                restored_cas.put(artifact)
            cls._prepare_relocated_workspace(
                staged=staged,
                restore_root=restore_root,
                workspace_record=workspace_record,
                source_root=source_root,
            )
            database = DuckDBExecutionStore(database_target)
            try:
                schema_row = database._connection.execute(
                    "SELECT max(version) FROM schema_migrations"
                ).fetchone()
                if schema_row is None or schema_row[0] is None:
                    raise BackupIntegrityError(
                        "restored database has no schema version"
                    )
                schema_version = int(schema_row[0])
                restored_artifact_ids = {
                    ArtifactID(row[0])
                    for row in database._connection.execute(
                        "SELECT artifact_id FROM artifact_payloads"
                    ).fetchall()
                }
            finally:
                database.close()
            report = ArtifactReachabilityValidator(
                database_path=database_target,
                payload_store=restored_cas,
            ).validate()
            if not report.integrity_ok or restored_artifact_ids != set(
                manifest.artifact_ids
            ):
                raise BackupIntegrityError(
                    "restored reachability does not match manifest"
                )
            os.rename(staged, restore_root)
        except Exception:
            if staged.exists():
                shutil.rmtree(staged)
            raise
        return RuntimeRestoreResult(
            backup_id=manifest.backup_id,
            manifest_sha256=manifest.manifest_sha256,
            restore_root=str(restore_root),
            database_sha256=cls._hash_file(restore_root / database_relative),
            artifact_count=len(manifest.artifact_ids),
            schema_version=schema_version,
            inspection_ready=True,
            offline_replay_ready=True,
        )

    @staticmethod
    def load_manifest(generation: Path) -> RuntimeBackupManifest:
        """Load and checksum-validate one backup manifest."""
        try:
            record = json.loads(
                (generation / "manifest.json").read_text(encoding="utf-8")
            )
            manifest_hash = record.pop("manifest_sha256")
            if (
                hashlib.sha256(
                    RuntimeBackupManager._canonical_bytes(record)
                ).hexdigest()
                != manifest_hash
            ):
                raise ValueError("manifest checksum mismatch")
            manifest = RuntimeBackupManifest(
                schema_version=record["schema_version"],
                backup_id=record["backup_id"],
                created_at=record["created_at"],
                database_sha256=record["database_sha256"],
                reachability_sha256=record["reachability_sha256"],
                artifact_ids=tuple(ArtifactID(item) for item in record["artifact_ids"]),
                artifact_payload_sha256=tuple(record["artifact_payload_sha256"]),
                workspace_files=tuple(
                    RuntimeBackupFile(
                        relative_path=item["relative_path"],
                        size_bytes=item["size_bytes"],
                        sha256=item["sha256"],
                    )
                    for item in record.get("workspace_files", [])
                ),
                manifest_sha256=manifest_hash,
            )
            if manifest.schema_version not in {
                "bijux.runtime.backup.v1",
                "bijux.runtime.backup.v2",
            }:
                raise ValueError("unsupported backup schema")
            if (
                len(manifest.artifact_ids)
                != len(manifest.artifact_payload_sha256)
                or tuple(sorted(manifest.artifact_ids)) != manifest.artifact_ids
                or len(set(manifest.artifact_ids)) != len(manifest.artifact_ids)
                or any(
                    re.fullmatch(r"sha256:[0-9a-f]{64}", str(item)) is None
                    for item in manifest.artifact_ids
                )
                or any(
                    re.fullmatch(r"[0-9a-f]{64}", item) is None
                    for item in manifest.artifact_payload_sha256
                )
            ):
                raise ValueError("backup artifact inventory is invalid")
            for item in manifest.workspace_files:
                RuntimeBackupManager._validate_workspace_file_relative_path(
                    item.relative_path
                )
                if (
                    isinstance(item.size_bytes, bool)
                    or not isinstance(item.size_bytes, int)
                    or item.size_bytes < 0
                    or re.fullmatch(r"[0-9a-f]{64}", item.sha256) is None
                ):
                    raise ValueError("backup workspace file inventory is invalid")
            if (
                tuple(
                    sorted(
                        manifest.workspace_files,
                        key=lambda item: item.relative_path,
                    )
                )
                != manifest.workspace_files
                or len({item.relative_path for item in manifest.workspace_files})
                != len(manifest.workspace_files)
            ):
                raise ValueError("backup workspace file inventory is invalid")
            return manifest
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise BackupIntegrityError("backup manifest is invalid") from exc

    @classmethod
    def _validate_generation(
        cls,
        generation: Path,
        manifest: RuntimeBackupManifest,
    ) -> None:
        if cls._hash_file(generation / "runtime.duckdb") != manifest.database_sha256:
            raise BackupIntegrityError(
                "existing backup database checksum does not match"
            )
        payload_store = AtomicFilesystemArtifactPayloadStore(generation / "cas")
        for artifact_id, payload_hash in zip(
            manifest.artifact_ids,
            manifest.artifact_payload_sha256,
            strict=True,
        ):
            try:
                artifact = payload_store.load(artifact_id)
            except (KeyError, PayloadCorruptionError, ValueError) as error:
                raise BackupIntegrityError(
                    "existing backup artifact content is absent or corrupt"
                ) from error
            if str(artifact.descriptor.payload_sha256) != payload_hash:
                raise BackupIntegrityError(
                    "existing backup payload checksum does not match"
                )
        for item in manifest.workspace_files:
            path = generation / "workspace" / item.relative_path
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size != item.size_bytes
                or cls._hash_file(path) != item.sha256
            ):
                raise BackupIntegrityError(
                    "existing backup workspace file checksum does not match"
                )

    def _copy_workspace_files(self, staged: Path) -> tuple[RuntimeBackupFile, ...]:
        root = self._layout.root
        required = (
            self._layout.manifest_path,
            self._layout.migration_ledger_path,
            self._layout.job_store_path,
        )
        for path in required:
            if not path.is_file() or path.is_symlink():
                raise BackupIntegrityError(
                    "backup requires canonical workspace control files"
                )
        selected_roots = [
            self._layout.index_root,
            self._layout.operations_root,
            self._layout.vex_root,
            self._layout.backup_root / "workspace-migrations",
        ]
        try:
            self._layout.model_root.relative_to(root)
        except ValueError as error:
            raise BackupIntegrityError(
                "backup cannot relocate a model stored outside the workspace; "
                "materialize the locked model below the workspace root"
            ) from error
        else:
            selected_roots.append(self._layout.model_root)
        sources = set(required)
        for selected_root in selected_roots:
            if not selected_root.exists():
                continue
            if selected_root.is_symlink() or not selected_root.is_dir():
                raise BackupIntegrityError(
                    "backup workspace state roots must be real directories"
                )
            for path in selected_root.rglob("*"):
                if path.is_symlink():
                    raise BackupIntegrityError(
                        "backup workspace state must not contain symbolic links"
                    )
                if path.is_file():
                    sources.add(path)
        records: list[RuntimeBackupFile] = []
        for source in sorted(sources):
            relative = source.relative_to(root).as_posix()
            self._validate_workspace_file_relative_path(relative)
            target = staged / "workspace" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            source_hash = self._hash_file(source)
            shutil.copy2(source, target)
            if (
                self._hash_file(source) != source_hash
                or self._hash_file(target) != source_hash
            ):
                raise BackupIntegrityError(
                    "workspace state changed while its backup was being created"
                )
            records.append(
                RuntimeBackupFile(
                    relative_path=relative,
                    size_bytes=target.stat().st_size,
                    sha256=source_hash,
                )
            )
        return tuple(records)

    @staticmethod
    def _validate_portable_relative_path(value: str) -> None:
        path = PurePosixPath(value)
        if (
            not value
            or value.startswith("/")
            or "\\" in value
            or path.as_posix() != value
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise BackupIntegrityError("backup workspace file path is invalid")

    @classmethod
    def _validate_workspace_file_relative_path(cls, value: str) -> None:
        cls._validate_portable_relative_path(value)
        path = PurePosixPath(value)
        if path.parts[0] == "cas" or value == "runtime.duckdb":
            raise BackupIntegrityError("backup workspace file path is reserved")

    @staticmethod
    def _load_workspace_record(path: Path) -> dict[str, object]:
        try:
            payload = path.read_bytes()
            record = json.loads(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BackupIntegrityError("backup workspace manifest is unreadable") from error
        if (
            not isinstance(record, dict)
            or canonical_json_bytes(record) != payload
            or record.get("schema_version") != "bijux.runtime.workspace.v5"
            or record.get("workspace_version") != 5
        ):
            raise BackupIntegrityError("backup workspace manifest is invalid")
        return record

    @staticmethod
    def _recorded_workspace_root(record: dict[str, object]) -> Path:
        layout = record.get("layout")
        if not isinstance(layout, dict) or not isinstance(layout.get("root"), str):
            raise BackupIntegrityError("backup workspace layout root is invalid")
        root = Path(layout["root"])
        if not root.is_absolute():
            raise BackupIntegrityError("backup workspace layout root is not absolute")
        return root

    @classmethod
    def _recorded_relative_path(
        cls,
        record: dict[str, object],
        field: str,
        *,
        source_root: Path,
    ) -> Path:
        layout = record.get("layout")
        value = layout.get(field) if isinstance(layout, dict) else None
        if not isinstance(value, str):
            raise BackupIntegrityError(f"backup workspace layout {field} is invalid")
        try:
            relative = Path(value).relative_to(source_root)
        except ValueError as error:
            raise BackupIntegrityError(
                f"backup workspace layout {field} is outside its root"
            ) from error
        cls._validate_portable_relative_path(relative.as_posix())
        return relative

    @classmethod
    def _prepare_relocated_workspace(
        cls,
        *,
        staged: Path,
        restore_root: Path,
        workspace_record: dict[str, object],
        source_root: Path,
    ) -> None:
        layout = workspace_record.get("layout")
        configuration = workspace_record.get("configuration")
        configured_layout = (
            configuration.get("workspace_layout")
            if isinstance(configuration, dict)
            else None
        )
        if (
            not isinstance(layout, dict)
            or not isinstance(configuration, dict)
            or not isinstance(configured_layout, dict)
        ):
            raise BackupIntegrityError("backup workspace layout records are invalid")

        def relocate_layout(record: dict[str, object]) -> dict[str, object]:
            relocated = dict(record)
            for field, value in record.items():
                if field in {"identity_sha256", "schema_version", "workspace_version"}:
                    continue
                if not isinstance(value, str):
                    raise BackupIntegrityError(
                        f"backup workspace layout {field} is invalid"
                    )
                try:
                    relative = Path(value).relative_to(source_root)
                except ValueError as error:
                    raise BackupIntegrityError(
                        f"backup workspace layout {field} is outside its root"
                    ) from error
                relocated[field] = str(restore_root / relative)
            return relocated

        relocated_layout = relocate_layout(layout)
        if relocate_layout(configured_layout) != relocated_layout:
            raise BackupIntegrityError(
                "backup workspace configuration and layout records disagree"
            )
        relocated_configuration = dict(configuration)
        relocated_configuration["workspace_layout"] = relocated_layout
        relocated_configuration["working_root"] = str(restore_root)
        for field in ("database_path", "embedding_model_path", "retrieval_index_path"):
            value = relocated_configuration.get(field)
            if value is None:
                continue
            if not isinstance(value, str):
                raise BackupIntegrityError(
                    f"backup workspace configuration {field} is invalid"
                )
            candidate = Path(value)
            if candidate.is_absolute():
                try:
                    relative = candidate.relative_to(source_root)
                except ValueError as error:
                    raise BackupIntegrityError(
                        f"backup workspace configuration {field} is external"
                    ) from error
                relocated_configuration[field] = str(restore_root / relative)
        relocated_record = {
            **workspace_record,
            "configuration": relocated_configuration,
            "layout": relocated_layout,
        }
        for field in (
            "cas_root",
            "index_root",
            "model_root",
            "operations_root",
            "vex_root",
            "locks_root",
            "staging_root",
            "temporary_root",
            "backup_root",
        ):
            relative = cls._recorded_relative_path(
                workspace_record,
                field,
                source_root=source_root,
            )
            (staged / relative).mkdir(parents=True, exist_ok=True)
        index_relative = cls._recorded_relative_path(
            workspace_record,
            "index_root",
            source_root=source_root,
        )
        (staged / index_relative / "generations").mkdir(
            parents=True,
            exist_ok=True,
        )
        manifest_relative = cls._recorded_relative_path(
            workspace_record,
            "manifest_path",
            source_root=source_root,
        )
        manifest_path = staged / manifest_relative
        manifest_path.write_bytes(canonical_json_bytes(relocated_record))

    @staticmethod
    def _canonical_bytes(record: dict[str, object]) -> bytes:
        return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_durable(path: Path, payload: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())


__all__ = [
    "BackupIntegrityError",
    "RuntimeBackupFile",
    "RuntimeBackupManager",
    "RuntimeBackupManifest",
    "RuntimeRestoreResult",
]
