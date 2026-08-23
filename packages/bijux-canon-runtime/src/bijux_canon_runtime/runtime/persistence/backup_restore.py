# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Consistent backup and verified clean-location restore."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
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
class RuntimeBackupManifest:
    """Checksummed identity of one database and reachable blob generation."""

    schema_version: str
    backup_id: str
    created_at: str
    database_sha256: str
    reachability_sha256: str
    artifact_ids: tuple[ArtifactID, ...]
    artifact_payload_sha256: tuple[str, ...]
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
        if not backup_id.strip():
            raise ValueError("backup_id must not be empty")
        destination = destination_root.resolve()
        generation = destination / "generations" / backup_id
        if generation.exists():
            manifest = self.load_manifest(generation)
            self._validate_generation(generation, manifest)
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
                report = ArtifactReachabilityValidator(
                    database_path=self._database_path,
                    payload_store=self._payload_store,
                ).validate()
                if not report.integrity_ok:
                    raise BackupIntegrityError(
                        "backup requires an integrity-clean reachable set"
                    )
                store._connection.execute("CHECKPOINT")
                shutil.copy2(self._database_path, staged / "runtime.duckdb")
                backup_cas = AtomicFilesystemArtifactPayloadStore(staged / "cas")
                payload_hashes: list[str] = []
                for artifact_id in report.reachable_artifact_ids:
                    artifact = self._payload_store.load(artifact_id)
                    backup_cas.put(artifact)
                    if backup_cas.load(artifact_id) != artifact:
                        raise BackupIntegrityError("backup blob verification failed")
                    payload_hashes.append(str(artifact.descriptor.payload_sha256))
            finally:
                store.close()
            unsigned: dict[str, object] = {
                "artifact_ids": [str(item) for item in report.reachable_artifact_ids],
                "artifact_payload_sha256": payload_hashes,
                "backup_id": backup_id,
                "created_at": created_at,
                "database_sha256": self._hash_file(staged / "runtime.duckdb"),
                "reachability_sha256": report.report_sha256,
                "schema_version": "bijux.runtime.backup.v1",
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
        source_database = backup_generation / "runtime.duckdb"
        if cls._hash_file(source_database) != manifest.database_sha256:
            raise BackupIntegrityError("backup database checksum does not match")
        staged = restore_root.with_name(restore_root.name + ".partial")
        if staged.exists():
            raise BackupIntegrityError("restore staging root already exists")
        staged.mkdir(parents=True)
        try:
            shutil.copy2(source_database, staged / "runtime.duckdb")
            source_cas = AtomicFilesystemArtifactPayloadStore(backup_generation / "cas")
            restored_cas = AtomicFilesystemArtifactPayloadStore(staged / "cas")
            for artifact_id, payload_hash in zip(
                manifest.artifact_ids,
                manifest.artifact_payload_sha256,
                strict=True,
            ):
                artifact = source_cas.load(artifact_id)
                if str(artifact.descriptor.payload_sha256) != payload_hash:
                    raise BackupIntegrityError("backup manifest payload hash mismatch")
                restored_cas.put(artifact)
            database = DuckDBExecutionStore(staged / "runtime.duckdb")
            try:
                schema_row = database._connection.execute(
                    "SELECT max(version) FROM schema_migrations"
                ).fetchone()
                if schema_row is None or schema_row[0] is None:
                    raise BackupIntegrityError(
                        "restored database has no schema version"
                    )
                schema_version = int(schema_row[0])
            finally:
                database.close()
            report = ArtifactReachabilityValidator(
                database_path=staged / "runtime.duckdb",
                payload_store=restored_cas,
            ).validate()
            if not report.integrity_ok or set(report.reachable_artifact_ids) != set(
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
            database_sha256=cls._hash_file(restore_root / "runtime.duckdb"),
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
            return RuntimeBackupManifest(
                schema_version=record["schema_version"],
                backup_id=record["backup_id"],
                created_at=record["created_at"],
                database_sha256=record["database_sha256"],
                reachability_sha256=record["reachability_sha256"],
                artifact_ids=tuple(ArtifactID(item) for item in record["artifact_ids"]),
                artifact_payload_sha256=tuple(record["artifact_payload_sha256"]),
                manifest_sha256=manifest_hash,
            )
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
            artifact = payload_store.load(artifact_id)
            if str(artifact.descriptor.payload_sha256) != payload_hash:
                raise BackupIntegrityError(
                    "existing backup payload checksum does not match"
                )

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
    "RuntimeBackupManager",
    "RuntimeBackupManifest",
    "RuntimeRestoreResult",
]
