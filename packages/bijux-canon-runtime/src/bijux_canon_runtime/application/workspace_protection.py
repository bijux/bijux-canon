# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application boundary for verified Runtime backup and clean-root restore."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from bijux_canon_runtime.application.runtime_configuration import RuntimeConfiguration
from bijux_canon_runtime.runtime.persistence import (
    BackupIntegrityError,
    RuntimeBackupManager,
)


class WorkspaceProtectionError(RuntimeError):
    """A workspace backup or restore request failed verification."""


class RuntimeWorkspaceProtection:
    """Expose verified lifecycle protection without transport-owned persistence."""

    def __init__(self, configuration: RuntimeConfiguration) -> None:
        self._manager = RuntimeBackupManager(configuration=configuration)

    def backup(
        self,
        *,
        backup_id: str,
        created_at: str | None = None,
    ) -> Mapping[str, object]:
        """Create or authenticate one configured backup generation."""
        timestamp = _timestamp(created_at)
        try:
            generation, manifest = self._manager.create_workspace_backup(
                backup_id=backup_id,
                created_at=timestamp,
            )
        except (BackupIntegrityError, OSError) as error:
            raise WorkspaceProtectionError(
                f"workspace backup failed: {error}"
            ) from error
        return {
            "backup_generation": str(generation),
            "manifest": {
                **asdict(manifest),
                "artifact_ids": [str(item) for item in manifest.artifact_ids],
                "artifact_payload_sha256": list(manifest.artifact_payload_sha256),
            },
            "schema_version": "bijux.runtime.workspace-backup-result.v1",
        }

    @staticmethod
    def restore(
        *,
        backup_generation: Path,
        restore_root: Path,
    ) -> Mapping[str, object]:
        """Restore an authenticated generation into one absent destination."""
        try:
            result = RuntimeBackupManager.restore(
                backup_generation=backup_generation,
                restore_root=restore_root,
            )
        except (BackupIntegrityError, OSError, ValueError) as error:
            raise WorkspaceProtectionError(
                f"workspace restore failed: {error}"
            ) from error
        return {
            **asdict(result),
            "schema_version": "bijux.runtime.workspace-restore-result.v1",
        }


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            "backup creation time must be an ISO-8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise ValueError("backup creation time must include a timezone")
    return parsed.isoformat()


__all__ = ["RuntimeWorkspaceProtection", "WorkspaceProtectionError"]
