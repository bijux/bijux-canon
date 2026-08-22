# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic export and offline verification of immutable evidence bundles."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from collections.abc import Iterable
from typing import Any

from bijux_canon_runtime.model.artifact import (
    AddressedArtifact,
    ImmutableArtifactDescriptor,
    canonical_json_bytes,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, ContentHash
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)


class EvidenceBundleIntegrityError(ValueError):
    """Raised when an exported bundle is incomplete, altered, or unsafe."""


@dataclass(frozen=True, slots=True)
class EvidenceBundleLimits:
    """Hard export and verification bounds for one evidence bundle."""

    max_artifacts: int = 10_000
    max_bundle_bytes: int = 1024 * 1024 * 1024
    max_artifact_bytes: int = 256 * 1024 * 1024
    max_manifest_bytes: int = 64 * 1024 * 1024
    stream_chunk_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if (
            min(
                self.max_artifacts,
                self.max_bundle_bytes,
                self.max_artifact_bytes,
                self.max_manifest_bytes,
                self.stream_chunk_bytes,
            )
            < 1
        ):
            raise ValueError("evidence bundle limits must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceRedactionPolicy:
    """Omit whole payloads while retaining their immutable descriptors."""

    policy_id: str
    redact_schema_ids: tuple[str, ...] = ()
    redact_artifact_ids: tuple[ArtifactID, ...] = ()
    schema_version: str = "bijux.runtime.evidence-redaction-policy.v1"

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("redaction policy identity must not be empty")
        if self.schema_version != "bijux.runtime.evidence-redaction-policy.v1":
            raise ValueError("unsupported evidence redaction policy schema")
        if len(set(self.redact_schema_ids)) != len(self.redact_schema_ids):
            raise ValueError("redaction schema identities must be unique")
        if len(set(self.redact_artifact_ids)) != len(self.redact_artifact_ids):
            raise ValueError("redaction artifact identities must be unique")

    def redacts(self, artifact: AddressedArtifact) -> bool:
        """Return whether exact bytes must be omitted for this artifact."""
        return self.redacts_descriptor(artifact.descriptor)

    def redacts_descriptor(self, descriptor: ImmutableArtifactDescriptor) -> bool:
        """Return whether a descriptor is covered by this omission policy."""
        return (
            descriptor.schema_id in self.redact_schema_ids
            or descriptor.artifact_id in self.redact_artifact_ids
        )

    def record(self) -> dict[str, object]:
        """Return the stable path-free policy record bound into a bundle."""
        return {
            "policy_id": self.policy_id,
            "redact_artifact_ids": sorted(
                str(item) for item in self.redact_artifact_ids
            ),
            "redact_schema_ids": sorted(self.redact_schema_ids),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundleManifest:
    """Stable identity and coverage summary for one exported bundle."""

    schema_version: str
    bundle_sha256: str
    root_artifact_ids: tuple[ArtifactID, ...]
    artifact_ids: tuple[ArtifactID, ...]
    redacted_artifact_ids: tuple[ArtifactID, ...]
    redaction_policy_id: str


@dataclass(frozen=True, slots=True)
class EvidenceBundleVerification:
    """Offline checksum and closure verdict for an exported bundle."""

    schema_version: str
    bundle_sha256: str
    valid: bool
    artifact_count: int
    included_payload_count: int
    redacted_payload_count: int
    complete_payloads: bool


class EvidenceBundleExporter:
    """Export dependency-complete evidence without mutable source locations."""

    def __init__(
        self,
        payload_store: AtomicFilesystemArtifactPayloadStore,
        *,
        limits: EvidenceBundleLimits = EvidenceBundleLimits(),
    ) -> None:
        self._payload_store = payload_store
        self._limits = limits

    def export(
        self,
        *,
        root_artifact_ids: tuple[ArtifactID, ...],
        destination: Path,
        redaction_policy: EvidenceRedactionPolicy,
    ) -> EvidenceBundleManifest:
        """Atomically create one deterministic immutable evidence bundle."""
        roots = tuple(sorted(set(root_artifact_ids)))
        if not roots:
            raise ValueError("evidence bundle requires at least one root artifact")
        destination = destination.resolve()
        if destination.exists():
            raise FileExistsError("evidence bundle destination already exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staged = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}.",
                suffix=".partial",
                dir=destination.parent,
            )
        )
        try:
            artifacts = self._dependency_closure(roots, redaction_policy)
            entries: list[dict[str, object]] = []
            redacted: list[ArtifactID] = []
            for artifact_id in sorted(artifacts):
                descriptor = artifacts[artifact_id]
                digest = str(artifact_id).removeprefix("sha256:")
                relative_root = PurePosixPath("objects", "sha256", digest[:2], digest)
                object_root = staged.joinpath(*relative_root.parts)
                object_root.mkdir(parents=True)
                descriptor_bytes = canonical_json_bytes(
                    self._descriptor_record(descriptor)
                )
                descriptor_file = relative_root / "descriptor.json"
                self._write_durable(object_root / "descriptor.json", descriptor_bytes)
                is_redacted = redaction_policy.redacts_descriptor(descriptor)
                payload_file: str | None = None
                disposition = "redacted" if is_redacted else "included"
                if is_redacted:
                    redacted.append(artifact_id)
                else:
                    payload_file = str(relative_root / "payload")
                    self._write_stream_durable(
                        object_root / "payload",
                        self._payload_store.iter_payload(
                            artifact_id,
                            chunk_bytes=self._limits.stream_chunk_bytes,
                        ),
                    )
                self._fsync_directory(object_root)
                entries.append(
                    {
                        "artifact_id": str(artifact_id),
                        "dependencies": [str(item) for item in descriptor.dependencies],
                        "descriptor_file": str(descriptor_file),
                        "descriptor_sha256": hashlib.sha256(
                            descriptor_bytes
                        ).hexdigest(),
                        "payload_disposition": disposition,
                        "payload_file": payload_file,
                        "payload_sha256": str(descriptor.payload_sha256),
                        "size_bytes": descriptor.size_bytes,
                    }
                )
            unsigned: dict[str, object] = {
                "artifacts": entries,
                "redaction_policy": redaction_policy.record(),
                "root_artifact_ids": [str(item) for item in roots],
                "schema_version": "bijux.runtime.evidence-bundle.v1",
            }
            bundle_hash = hashlib.sha256(self._canonical_bytes(unsigned)).hexdigest()
            manifest_record = {**unsigned, "bundle_sha256": bundle_hash}
            self._write_durable(
                staged / "manifest.json",
                json.dumps(manifest_record, indent=2, sort_keys=True).encode("utf-8")
                + b"\n",
            )
            self._fsync_tree(staged)
            staged_verification = self.verify_export(staged, limits=self._limits)
            if (
                not staged_verification.valid
                or staged_verification.bundle_sha256 != bundle_hash
            ):
                raise EvidenceBundleIntegrityError("staged evidence bundle is invalid")
            os.rename(staged, destination)
            self._fsync_directory(destination.parent)
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        manifest = EvidenceBundleManifest(
            schema_version="bijux.runtime.evidence-bundle.v1",
            bundle_sha256=bundle_hash,
            root_artifact_ids=roots,
            artifact_ids=tuple(sorted(artifacts)),
            redacted_artifact_ids=tuple(sorted(redacted)),
            redaction_policy_id=redaction_policy.policy_id,
        )
        verified = self.verify_export(destination, limits=self._limits)
        if not verified.valid or verified.bundle_sha256 != manifest.bundle_sha256:
            raise EvidenceBundleIntegrityError("exported evidence bundle is invalid")
        return manifest

    @classmethod
    def verify_export(
        cls,
        bundle_root: Path,
        *,
        limits: EvidenceBundleLimits = EvidenceBundleLimits(),
    ) -> EvidenceBundleVerification:
        """Verify one bundle offline using only its stable relative manifest."""
        bundle_root = bundle_root.resolve()
        try:
            manifest_path = bundle_root / "manifest.json"
            if manifest_path.stat().st_size > limits.max_manifest_bytes:
                raise ValueError("evidence bundle manifest exceeds its byte limit")
            record = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ValueError("manifest must be an object")
            bundle_hash = record.pop("bundle_sha256")
            if set(record) != {
                "artifacts",
                "redaction_policy",
                "root_artifact_ids",
                "schema_version",
            }:
                raise ValueError("manifest fields do not match its stable schema")
            if (
                not isinstance(bundle_hash, str)
                or hashlib.sha256(cls._canonical_bytes(record)).hexdigest()
                != bundle_hash
            ):
                raise ValueError("manifest checksum does not match")
            if record.get("schema_version") != "bijux.runtime.evidence-bundle.v1":
                raise ValueError("unsupported evidence bundle schema")
            policy_record = record["redaction_policy"]
            if not isinstance(policy_record, dict):
                raise ValueError("redaction policy must be an object")
            if set(policy_record) != {
                "policy_id",
                "redact_artifact_ids",
                "redact_schema_ids",
                "schema_version",
            }:
                raise ValueError("redaction policy fields do not match its schema")
            policy = EvidenceRedactionPolicy(
                policy_id=policy_record["policy_id"],
                redact_schema_ids=tuple(policy_record["redact_schema_ids"]),
                redact_artifact_ids=tuple(
                    ArtifactID(item) for item in policy_record["redact_artifact_ids"]
                ),
                schema_version=policy_record["schema_version"],
            )
            entries = record["artifacts"]
            roots = record["root_artifact_ids"]
            if not isinstance(entries, list) or not isinstance(roots, list):
                raise ValueError("manifest artifact collections are invalid")
            if len(entries) > limits.max_artifacts:
                raise ValueError("evidence bundle exceeds its artifact limit")
            expected_files = {"manifest.json"}
            artifact_ids: set[str] = set()
            dependency_ids: set[str] = set()
            included = 0
            redacted = 0
            included_bytes = 0
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("artifact entry must be an object")
                if set(entry) != {
                    "artifact_id",
                    "dependencies",
                    "descriptor_file",
                    "descriptor_sha256",
                    "payload_disposition",
                    "payload_file",
                    "payload_sha256",
                    "size_bytes",
                }:
                    raise ValueError("artifact entry fields do not match its schema")
                artifact_id = entry["artifact_id"]
                if not isinstance(artifact_id, str) or artifact_id in artifact_ids:
                    raise ValueError("artifact identities must be unique strings")
                artifact_ids.add(artifact_id)
                dependencies = entry["dependencies"]
                if not isinstance(dependencies, list):
                    raise ValueError("artifact dependencies must be a list")
                dependency_ids.update(dependencies)
                descriptor_path = cls._safe_bundle_path(
                    bundle_root,
                    entry["descriptor_file"],
                )
                expected_files.add(str(descriptor_path.relative_to(bundle_root)))
                if descriptor_path.stat().st_size > limits.max_manifest_bytes:
                    raise ValueError("artifact descriptor exceeds its byte limit")
                descriptor_bytes = descriptor_path.read_bytes()
                if hashlib.sha256(descriptor_bytes).hexdigest() != entry.get(
                    "descriptor_sha256"
                ):
                    raise ValueError("artifact descriptor checksum does not match")
                descriptor_record = json.loads(descriptor_bytes)
                descriptor = cls._descriptor_from_record(descriptor_record)
                if str(descriptor.artifact_id) != artifact_id:
                    raise ValueError("descriptor identity does not match manifest")
                disposition = entry.get("payload_disposition")
                if disposition == "included":
                    if policy.redacts_descriptor(descriptor):
                        raise ValueError("redacted artifact includes payload bytes")
                    payload_path = cls._safe_bundle_path(
                        bundle_root,
                        entry["payload_file"],
                    )
                    expected_files.add(str(payload_path.relative_to(bundle_root)))
                    if descriptor.size_bytes > limits.max_artifact_bytes:
                        raise ValueError("artifact payload exceeds its byte limit")
                    included_bytes += descriptor.size_bytes
                    if included_bytes > limits.max_bundle_bytes:
                        raise ValueError("bundle payloads exceed their byte limit")
                    cls._verify_payload_file(
                        payload_path,
                        descriptor,
                        chunk_bytes=limits.stream_chunk_bytes,
                    )
                    if descriptor.size_bytes != entry.get("size_bytes"):
                        raise ValueError("artifact size does not match manifest")
                    if str(descriptor.payload_sha256) != entry.get("payload_sha256"):
                        raise ValueError("artifact payload checksum does not match")
                    included += 1
                elif disposition == "redacted" and entry.get("payload_file") is None:
                    if not policy.redacts_descriptor(descriptor):
                        raise ValueError("artifact is redacted outside declared policy")
                    redacted += 1
                else:
                    raise ValueError("artifact payload disposition is invalid")
            if not set(roots).issubset(artifact_ids):
                raise ValueError("bundle root is absent from artifact closure")
            if not dependency_ids.issubset(artifact_ids):
                raise ValueError("bundle dependency closure is incomplete")
            actual_files: set[str] = set()
            max_files = limits.max_artifacts * 2 + 1
            for path in bundle_root.rglob("*"):
                if not path.is_file():
                    continue
                if len(actual_files) >= max_files:
                    raise ValueError("bundle file inventory exceeds its limit")
                actual_files.add(str(path.relative_to(bundle_root)))
            if actual_files != expected_files:
                raise ValueError("bundle file inventory does not match manifest")
        except (
            KeyError,
            OSError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise EvidenceBundleIntegrityError(
                "evidence bundle verification failed"
            ) from exc
        return EvidenceBundleVerification(
            schema_version="bijux.runtime.evidence-bundle-verification.v1",
            bundle_sha256=bundle_hash,
            valid=True,
            artifact_count=len(entries),
            included_payload_count=included,
            redacted_payload_count=redacted,
            complete_payloads=redacted == 0,
        )

    def _dependency_closure(
        self,
        roots: tuple[ArtifactID, ...],
        redaction_policy: EvidenceRedactionPolicy,
    ) -> dict[ArtifactID, ImmutableArtifactDescriptor]:
        artifacts: dict[ArtifactID, ImmutableArtifactDescriptor] = {}
        pending = list(roots)
        included_bytes = 0
        while pending:
            artifact_id = pending.pop()
            if artifact_id in artifacts:
                continue
            descriptor = self._payload_store.load_descriptor(artifact_id)
            if len(artifacts) >= self._limits.max_artifacts:
                raise ValueError("evidence bundle exceeds its artifact limit")
            if not redaction_policy.redacts_descriptor(descriptor):
                if descriptor.size_bytes > self._limits.max_artifact_bytes:
                    raise ValueError("artifact payload exceeds its byte limit")
                included_bytes += descriptor.size_bytes
                if included_bytes > self._limits.max_bundle_bytes:
                    raise ValueError("bundle payloads exceed their byte limit")
            artifacts[artifact_id] = descriptor
            pending.extend(descriptor.dependencies)
        return artifacts

    @staticmethod
    def _verify_payload_file(
        path: Path,
        descriptor: ImmutableArtifactDescriptor,
        *,
        chunk_bytes: int,
    ) -> None:
        payload_hash = hashlib.sha256()
        identity_hash = hashlib.sha256()
        identity_hash.update(descriptor.schema_id.encode("utf-8"))
        identity_hash.update(b"\0")
        identity_hash.update(descriptor.media_type.encode("ascii"))
        identity_hash.update(b"\0")
        size_bytes = 0
        with path.open("rb") as stream:
            while chunk := stream.read(chunk_bytes):
                size_bytes += len(chunk)
                payload_hash.update(chunk)
                identity_hash.update(chunk)
        if (
            size_bytes != descriptor.size_bytes
            or payload_hash.hexdigest() != str(descriptor.payload_sha256)
            or "sha256:" + identity_hash.hexdigest() != str(descriptor.artifact_id)
        ):
            raise ValueError("artifact payload identity does not match descriptor")

    @staticmethod
    def _safe_bundle_path(bundle_root: Path, value: Any) -> Path:
        if not isinstance(value, str):
            raise ValueError("bundle file path must be a string")
        relative = PurePosixPath(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("bundle file path escapes its immutable root")
        resolved = bundle_root.joinpath(*relative.parts).resolve()
        if not resolved.is_relative_to(bundle_root):
            raise ValueError("bundle file path escapes its immutable root")
        return resolved

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

    @staticmethod
    def _descriptor_from_record(record: Any) -> ImmutableArtifactDescriptor:
        if not isinstance(record, dict):
            raise ValueError("artifact descriptor must be an object")
        dependencies = record["dependencies"]
        if not isinstance(dependencies, list):
            raise ValueError("artifact descriptor dependencies must be a list")
        return ImmutableArtifactDescriptor(
            artifact_id=ArtifactID(record["artifact_id"]),
            schema_id=record["schema_id"],
            media_type=record["media_type"],
            size_bytes=record["size_bytes"],
            payload_sha256=ContentHash(record["payload_sha256"]),
            producer=record["producer"],
            dependencies=tuple(ArtifactID(item) for item in dependencies),
        )

    @staticmethod
    def _canonical_bytes(record: dict[str, object]) -> bytes:
        return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _write_durable(path: Path, payload: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _write_stream_durable(path: Path, chunks: Iterable[bytes]) -> None:
        with path.open("xb") as stream:
            for chunk in chunks:
                stream.write(chunk)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @classmethod
    def _fsync_tree(cls, root: Path) -> None:
        for directory in sorted(
            (path for path in root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            cls._fsync_directory(directory)
        cls._fsync_directory(root)


__all__ = [
    "EvidenceBundleExporter",
    "EvidenceBundleIntegrityError",
    "EvidenceBundleLimits",
    "EvidenceBundleManifest",
    "EvidenceBundleVerification",
    "EvidenceRedactionPolicy",
]
