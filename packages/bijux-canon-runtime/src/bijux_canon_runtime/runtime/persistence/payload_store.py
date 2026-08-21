# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Complete immutable artifact payload storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.ontology.ids import ArtifactID, TenantID


class PayloadCollisionError(ValueError):
    """Raised when one immutable identity is presented with different content."""


@dataclass(frozen=True, slots=True)
class PayloadBinding:
    """Tenant-scoped runtime name bound to one immutable payload."""

    tenant_id: TenantID
    logical_artifact_id: ArtifactID
    target_artifact_id: ArtifactID


class ArtifactPayloadStore(ABC):
    """Storage contract for complete immutable payloads and runtime bindings."""

    @abstractmethod
    def put(self, artifact: AddressedArtifact) -> None:
        """Store canonical bytes and their complete verified descriptor."""
        raise NotImplementedError

    @abstractmethod
    def load(self, artifact_id: ArtifactID) -> AddressedArtifact:
        """Load and revalidate a complete immutable payload."""
        raise NotImplementedError

    @abstractmethod
    def bind(
        self,
        *,
        tenant_id: TenantID,
        logical_artifact_id: ArtifactID,
        target_artifact_id: ArtifactID,
    ) -> PayloadBinding:
        """Bind a runtime artifact name without changing immutable content."""
        raise NotImplementedError

    @abstractmethod
    def binding(
        self, logical_artifact_id: ArtifactID, *, tenant_id: TenantID
    ) -> PayloadBinding:
        """Resolve a tenant-scoped runtime artifact name."""
        raise NotImplementedError

    def resolve(
        self, logical_artifact_id: ArtifactID, *, tenant_id: TenantID
    ) -> AddressedArtifact:
        """Load the immutable payload selected by a runtime artifact name."""
        return self.load(
            self.binding(logical_artifact_id, tenant_id=tenant_id).target_artifact_id
        )


class InMemoryArtifactPayloadStore(ArtifactPayloadStore):
    """Deterministic complete-payload store for an explicitly bounded run."""

    def __init__(self) -> None:
        self._payloads: dict[ArtifactID, AddressedArtifact] = {}
        self._bindings: dict[tuple[TenantID, ArtifactID], PayloadBinding] = {}

    def put(self, artifact: AddressedArtifact) -> None:
        artifact_id = artifact.descriptor.artifact_id
        existing = self._payloads.get(artifact_id)
        if existing is not None and existing != artifact:
            raise PayloadCollisionError(
                "immutable artifact identity has conflicting payload metadata"
            )
        self._payloads[artifact_id] = artifact

    def load(self, artifact_id: ArtifactID) -> AddressedArtifact:
        try:
            artifact = self._payloads[artifact_id]
        except KeyError as exc:
            raise KeyError(f"Artifact payload not found: {artifact_id}") from exc
        # Reconstructing the value invokes AddressedArtifact's integrity check.
        return AddressedArtifact(
            descriptor=artifact.descriptor,
            canonical_bytes=artifact.canonical_bytes,
        )

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


__all__ = [
    "ArtifactPayloadStore",
    "InMemoryArtifactPayloadStore",
    "PayloadBinding",
    "PayloadCollisionError",
]
