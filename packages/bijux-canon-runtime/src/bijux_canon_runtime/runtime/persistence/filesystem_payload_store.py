# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Durable atomic filesystem storage for immutable artifact payloads."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from bijux_canon_runtime.model.artifact import (
    AddressedArtifact,
    ImmutableArtifactDescriptor,
    canonical_json_bytes,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, ContentHash, TenantID
from bijux_canon_runtime.runtime.persistence.payload_store import (
    ArtifactPayloadStore,
    PayloadBinding,
    PayloadCollisionError,
)


class PayloadCorruptionError(ValueError):
    """Raised when durable bytes or metadata fail content validation."""


class AtomicFilesystemArtifactPayloadStore(ArtifactPayloadStore):
    """Publish complete payload generations atomically under a bounded root."""

    _DESCRIPTOR_KEYS = {
        "artifact_id",
        "dependencies",
        "media_type",
        "payload_sha256",
        "producer",
        "schema_id",
        "size_bytes",
    }

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._objects = self._root / "objects" / "sha256"
        self._staging = self._root / "staging"
        self._bindings: dict[tuple[TenantID, ArtifactID], PayloadBinding] = {}
        self._objects.mkdir(parents=True, exist_ok=True)
        self._staging.mkdir(parents=True, exist_ok=True)
        self.cleanup_abandoned_writes()

    @property
    def root(self) -> Path:
        """Return the explicit storage authority root."""
        return self._root

    def put(self, artifact: AddressedArtifact) -> None:
        verified = AddressedArtifact(
            descriptor=artifact.descriptor,
            canonical_bytes=artifact.canonical_bytes,
        )
        target = self._artifact_directory(verified.descriptor.artifact_id)
        if target.exists():
            self._require_identical_existing(verified)
            return

        prefix_existed = target.parent.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        if not prefix_existed:
            self._fsync_directory(self._objects)
        staged = Path(
            tempfile.mkdtemp(
                prefix=f"{target.name}.{os.getpid()}.",
                suffix=".partial",
                dir=self._staging,
            )
        )
        try:
            self._write_durable(staged / "payload", verified.canonical_bytes)
            descriptor_bytes = canonical_json_bytes(
                self._descriptor_record(verified.descriptor)
            )
            self._write_durable(staged / "descriptor.json", descriptor_bytes)
            self._write_durable(
                staged / "descriptor.sha256",
                (hashlib.sha256(descriptor_bytes).hexdigest() + "\n").encode("ascii"),
            )
            self._fsync_directory(staged)
            try:
                os.rename(staged, target)
            except OSError:
                if not target.exists():
                    raise
                self._require_identical_existing(verified)
            self._fsync_directory(target.parent)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
                self._fsync_directory(self._staging)

        self._require_identical_existing(verified)

    def load(self, artifact_id: ArtifactID) -> AddressedArtifact:
        directory = self._artifact_directory(artifact_id)
        if not directory.is_dir():
            raise KeyError(f"Artifact payload not found: {artifact_id}")
        try:
            descriptor_bytes = (directory / "descriptor.json").read_bytes()
            expected_descriptor_hash = (
                directory / "descriptor.sha256"
            ).read_text(encoding="ascii").strip()
            actual_descriptor_hash = hashlib.sha256(descriptor_bytes).hexdigest()
            if expected_descriptor_hash != actual_descriptor_hash:
                raise ValueError("artifact descriptor checksum does not match")
            descriptor_record = json.loads(descriptor_bytes)
            descriptor = self._descriptor_from_record(descriptor_record)
            payload = (directory / "payload").read_bytes()
            artifact = AddressedArtifact(
                descriptor=descriptor,
                canonical_bytes=payload,
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PayloadCorruptionError(
                f"Artifact payload failed validation: {artifact_id}"
            ) from exc
        if artifact.descriptor.artifact_id != artifact_id:
            raise PayloadCorruptionError(
                f"Artifact path identity does not match descriptor: {artifact_id}"
            )
        return artifact

    def bind(
        self,
        *,
        tenant_id: TenantID,
        logical_artifact_id: ArtifactID,
        target_artifact_id: ArtifactID,
    ) -> PayloadBinding:
        self.load(target_artifact_id)
        key = (tenant_id, logical_artifact_id)
        binding = PayloadBinding(
            tenant_id=tenant_id,
            logical_artifact_id=logical_artifact_id,
            target_artifact_id=target_artifact_id,
        )
        existing = self._bindings.get(key)
        if existing is not None and existing != binding:
            raise PayloadCollisionError(
                "runtime artifact name is already bound to another payload"
            )
        self._bindings[key] = binding
        return binding

    def binding(
        self, logical_artifact_id: ArtifactID, *, tenant_id: TenantID
    ) -> PayloadBinding:
        try:
            return self._bindings[(tenant_id, logical_artifact_id)]
        except KeyError as exc:
            raise KeyError(
                f"Artifact payload binding not found: {logical_artifact_id}"
            ) from exc

    def cleanup_abandoned_writes(self) -> int:
        """Remove only unpublished staging entries below this store's root."""
        removed = 0
        for entry in self._staging.iterdir():
            if not entry.name.endswith(".partial"):
                continue
            owner_pid = self._staging_owner_pid(entry)
            if owner_pid is not None and self._process_exists(owner_pid):
                continue
            if entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed += 1
        if removed:
            self._fsync_directory(self._staging)
        return removed

    @staticmethod
    def _staging_owner_pid(entry: Path) -> int | None:
        parts = entry.name.split(".")
        if len(parts) < 4 or not parts[-2]:
            return None
        try:
            pid = int(parts[-3])
        except ValueError:
            return None
        return pid if pid > 0 else None

    @staticmethod
    def _process_exists(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def artifact_ids(self) -> tuple[ArtifactID, ...]:
        """Inventory immutable object paths without trusting their contents."""
        identities: list[ArtifactID] = []
        for prefix in self._objects.iterdir():
            if prefix.is_symlink() or not prefix.is_dir():
                continue
            for entry in prefix.iterdir():
                if entry.is_symlink() or not entry.is_dir():
                    continue
                digest = entry.name
                if (
                    len(digest) == 64
                    and prefix.name == digest[:2]
                    and all(char in "0123456789abcdef" for char in digest)
                ):
                    identities.append(ArtifactID(f"sha256:{digest}"))
        return tuple(sorted(identities))

    def artifact_directory(self, artifact_id: ArtifactID) -> Path:
        """Return the validated directory for one immutable identity."""
        return self._artifact_directory(artifact_id)

    def _artifact_directory(self, artifact_id: ArtifactID) -> Path:
        value = str(artifact_id)
        if not value.startswith("sha256:") or len(value) != 71:
            raise ValueError("filesystem payload identity must be a SHA-256 artifact ID")
        digest = value.removeprefix("sha256:")
        if any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("filesystem payload identity must use lowercase hex")
        return self._objects / digest[:2] / digest

    def _require_identical_existing(self, artifact: AddressedArtifact) -> None:
        try:
            existing = self.load(artifact.descriptor.artifact_id)
        except (KeyError, PayloadCorruptionError) as exc:
            raise PayloadCollisionError(
                "immutable artifact identity points to corrupt durable content"
            ) from exc
        if existing != artifact:
            raise PayloadCollisionError(
                "immutable artifact identity has conflicting durable content"
            )

    @staticmethod
    def _write_durable(path: Path, payload: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _descriptor_record(
        descriptor: ImmutableArtifactDescriptor,
    ) -> dict[str, object]:
        return {
            "artifact_id": str(descriptor.artifact_id),
            "dependencies": [str(item) for item in descriptor.dependencies],
            "media_type": descriptor.media_type,
            "payload_sha256": str(descriptor.payload_sha256),
            "producer": descriptor.producer,
            "schema_id": descriptor.schema_id,
            "size_bytes": descriptor.size_bytes,
        }

    @classmethod
    def _descriptor_from_record(
        cls, record: Any
    ) -> ImmutableArtifactDescriptor:
        if not isinstance(record, dict) or set(record) != cls._DESCRIPTOR_KEYS:
            raise ValueError("artifact descriptor has an invalid shape")
        string_fields = (
            "artifact_id",
            "media_type",
            "payload_sha256",
            "producer",
            "schema_id",
        )
        if any(not isinstance(record[field], str) for field in string_fields):
            raise ValueError("artifact descriptor string field is invalid")
        if isinstance(record["size_bytes"], bool) or not isinstance(
            record["size_bytes"], int
        ):
            raise ValueError("artifact descriptor size is invalid")
        dependencies = record["dependencies"]
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise ValueError("artifact descriptor dependencies are invalid")
        return ImmutableArtifactDescriptor(
            artifact_id=ArtifactID(record["artifact_id"]),
            schema_id=record["schema_id"],
            media_type=record["media_type"],
            size_bytes=record["size_bytes"],
            payload_sha256=ContentHash(record["payload_sha256"]),
            producer=record["producer"],
            dependencies=tuple(ArtifactID(item) for item in dependencies),
        )


__all__ = [
    "AtomicFilesystemArtifactPayloadStore",
    "PayloadCorruptionError",
]
