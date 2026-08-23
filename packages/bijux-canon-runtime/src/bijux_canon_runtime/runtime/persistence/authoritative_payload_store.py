# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Filesystem CAS whose durable relationships are registered in DuckDB."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
import threading

from bijux_canon_runtime.model.artifact import (
    AddressedArtifact,
    ImmutableArtifactDescriptor,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, TenantID
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.persistence.metadata_authority import (
    DuckDBMetadataAuthority,
    MetadataIntegrityError,
)
from bijux_canon_runtime.runtime.persistence.payload_store import (
    ArtifactPayloadStore,
    PayloadBinding,
)


class AuthoritativeArtifactPayloadStore(ArtifactPayloadStore):
    """Publish immutable bytes before making their metadata reachable.

    A failed metadata transaction can leave an unreachable CAS object, which is
    safe to collect.  The reverse ordering is forbidden: DuckDB must never point
    at bytes that were not durably published and revalidated first.
    """

    def __init__(
        self,
        *,
        payload_store: AtomicFilesystemArtifactPayloadStore,
        database_path: Path,
        lock_timeout_seconds: float = 5.0,
    ) -> None:
        if not database_path.is_absolute():
            raise ValueError("metadata authority database path must be absolute")
        self._payload_store = payload_store
        self._database_path = database_path
        self._lock_timeout_seconds = lock_timeout_seconds
        self._lock = threading.RLock()

    @property
    def root(self) -> Path:
        """Return the underlying content-addressed storage root."""
        return self._payload_store.root

    def put(self, artifact: AddressedArtifact) -> None:
        """Durably store and verify bytes, then register their exact descriptor."""
        with self._lock:
            self._payload_store.put(artifact)
            verified = self._payload_store.load(artifact.descriptor.artifact_id)
            if verified != artifact:
                raise ValueError("durable payload changed before metadata registration")
            with DuckDBMetadataAuthority(
                self._database_path,
                lock_timeout_seconds=self._lock_timeout_seconds,
            ) as authority:
                authority.register_payload(
                    verified.descriptor,
                    created_at=datetime.now(UTC).isoformat(),
                )

    def load(self, artifact_id: ArtifactID) -> AddressedArtifact:
        """Load and revalidate bytes from the filesystem authority."""
        return self._payload_store.load(artifact_id)

    def load_descriptor(self, artifact_id: ArtifactID) -> ImmutableArtifactDescriptor:
        """Load and validate immutable metadata without materializing bytes."""
        return self._payload_store.load_descriptor(artifact_id)

    def iter_payload(
        self,
        artifact_id: ArtifactID,
        *,
        chunk_bytes: int = 1024 * 1024,
    ) -> Iterator[bytes]:
        """Stream a payload through the filesystem integrity boundary."""
        return self._payload_store.iter_payload(
            artifact_id,
            chunk_bytes=chunk_bytes,
        )

    def iter_artifact_ids(self) -> Iterator[ArtifactID]:
        """Iterate the deterministic durable CAS inventory."""
        return self._payload_store.iter_artifact_ids()

    def cleanup_abandoned_writes(self) -> int:
        """Remove only incomplete filesystem publications."""
        return self._payload_store.cleanup_abandoned_writes()

    def bind(
        self,
        *,
        tenant_id: TenantID,
        logical_artifact_id: ArtifactID,
        target_artifact_id: ArtifactID,
    ) -> PayloadBinding:
        """Retain the legacy process-local binding contract.

        Durable run-scoped references are recorded by publication transactions;
        this method remains only for callers of the older payload-store protocol.
        """
        return self._payload_store.bind(
            tenant_id=tenant_id,
            logical_artifact_id=logical_artifact_id,
            target_artifact_id=target_artifact_id,
        )

    def binding(
        self, logical_artifact_id: ArtifactID, *, tenant_id: TenantID
    ) -> PayloadBinding:
        """Resolve a legacy process-local binding."""
        return self._payload_store.binding(
            logical_artifact_id,
            tenant_id=tenant_id,
        )

    def reconcile_inventory(self, *, max_artifacts: int = 100_000) -> int:
        """Admit a prior CAS inventory and fail closed on split authority."""
        if max_artifacts < 1:
            raise ValueError("payload reconciliation bound must be positive")
        with self._lock:
            artifact_ids = tuple(self._payload_store.iter_artifact_ids())
            if len(artifact_ids) > max_artifacts:
                raise MetadataIntegrityError(
                    "CAS inventory exceeds the reconciliation bound"
                )
            inventory = set(artifact_ids)
            descriptors = {
                artifact_id: self._payload_store.load_descriptor(artifact_id)
                for artifact_id in artifact_ids
            }
            missing_dependencies = {
                dependency
                for descriptor in descriptors.values()
                for dependency in descriptor.dependencies
                if dependency not in inventory
            }
            if missing_dependencies:
                raise MetadataIntegrityError(
                    "CAS inventory contains artifacts with missing dependencies"
                )
            with DuckDBMetadataAuthority(
                self._database_path,
                lock_timeout_seconds=self._lock_timeout_seconds,
            ) as authority:
                registered = set(authority.payload_ids())
                if registered - inventory:
                    raise MetadataIntegrityError(
                        "DuckDB payload metadata points to absent CAS content"
                    )
                pending = inventory - registered
                admitted = 0
                while pending:
                    ready = sorted(
                        artifact_id
                        for artifact_id in pending
                        if set(descriptors[artifact_id].dependencies) <= registered
                    )
                    if not ready:
                        raise MetadataIntegrityError(
                            "CAS dependency graph cannot be reconciled"
                        )
                    for artifact_id in ready:
                        descriptor_path = (
                            self._payload_store.root
                            / "objects"
                            / "sha256"
                            / str(artifact_id).removeprefix("sha256:")[:2]
                            / str(artifact_id).removeprefix("sha256:")
                            / "descriptor.json"
                        )
                        created_at = datetime.fromtimestamp(
                            descriptor_path.stat().st_mtime,
                            tz=UTC,
                        ).isoformat()
                        authority.register_payload(
                            descriptors[artifact_id],
                            created_at=created_at,
                        )
                        registered.add(artifact_id)
                        pending.remove(artifact_id)
                        admitted += 1
                return admitted


__all__ = ["AuthoritativeArtifactPayloadStore"]
