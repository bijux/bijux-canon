# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/artifact_store.py."""

from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib

from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
)
from agentic_flows.spec.ontology.ids import ArtifactID, ContentHash, TenantID


class ArtifactStore(ABC):
    """Behavioral contract for ArtifactStore."""

    @abstractmethod
    def create(
        self,
        *,
        spec_version: str,
        artifact_id: ArtifactID,
        tenant_id: TenantID,
        artifact_type: ArtifactType,
        producer: str,
        parent_artifacts: tuple[ArtifactID, ...],
        content_hash: ContentHash,
        scope: ArtifactScope,
    ) -> Artifact:
        """Execute create and enforce its contract."""
        raise NotImplementedError

    @abstractmethod
    def save(self, artifact: Artifact) -> None:
        """Execute save and enforce its contract."""
        raise NotImplementedError

    @abstractmethod
    def load(self, artifact_id: ArtifactID, *, tenant_id: TenantID) -> Artifact:
        """Execute load and enforce its contract."""
        raise NotImplementedError


class InMemoryArtifactStore(ArtifactStore):
    """Behavioral contract for InMemoryArtifactStore."""

    def __init__(self) -> None:
        """Internal helper; not part of the public API."""
        self._items: dict[tuple[TenantID, ArtifactID], Artifact] = {}

    def create(
        self,
        *,
        spec_version: str,
        artifact_id: ArtifactID,
        tenant_id: TenantID,
        artifact_type: ArtifactType,
        producer: str,
        parent_artifacts: tuple[ArtifactID, ...],
        content_hash: ContentHash,
        scope: ArtifactScope,
    ) -> Artifact:
        """Execute create and enforce its contract."""
        artifact = Artifact(
            spec_version=spec_version,
            artifact_id=artifact_id,
            tenant_id=tenant_id,
            artifact_type=artifact_type,
            producer=producer,
            parent_artifacts=parent_artifacts,
            content_hash=content_hash,
            scope=scope,
        )
        self.save(artifact)
        return artifact

    def save(self, artifact: Artifact) -> None:
        """Execute save and enforce its contract."""
        key = (artifact.tenant_id, artifact.artifact_id)
        existing = self._items.get(key)
        if existing is not None:
            raise ValueError("Artifact IDs must be unique per run")
        self._items[key] = artifact

    def load(self, artifact_id: ArtifactID, *, tenant_id: TenantID) -> Artifact:
        """Execute load and enforce its contract."""
        key = (tenant_id, artifact_id)
        if key not in self._items:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return self._items[key]


class HostileArtifactStore(ArtifactStore):
    """Behavioral contract for HostileArtifactStore."""

    def __init__(
        self,
        *,
        seed: int,
        max_delay: int = 2,
        drop_rate: float = 0.2,
        corruption_rate: float = 0.2,
    ) -> None:
        """Internal helper; not part of the public API."""
        self._seed = seed
        self._max_delay = max_delay
        self._drop_rate = drop_rate
        self._corruption_rate = corruption_rate
        self._items: dict[tuple[TenantID, ArtifactID], Artifact] = {}
        self._pending: dict[tuple[TenantID, ArtifactID], tuple[Artifact, int]] = {}

    def create(
        self,
        *,
        spec_version: str,
        artifact_id: ArtifactID,
        tenant_id: TenantID,
        artifact_type: ArtifactType,
        producer: str,
        parent_artifacts: tuple[ArtifactID, ...],
        content_hash: ContentHash,
        scope: ArtifactScope,
    ) -> Artifact:
        """Execute create and enforce its contract."""
        artifact = Artifact(
            spec_version=spec_version,
            artifact_id=artifact_id,
            tenant_id=tenant_id,
            artifact_type=artifact_type,
            producer=producer,
            parent_artifacts=parent_artifacts,
            content_hash=content_hash,
            scope=scope,
        )
        self.save(artifact)
        return artifact

    def save(self, artifact: Artifact) -> None:
        """Execute save and enforce its contract."""
        key = (artifact.tenant_id, artifact.artifact_id)
        existing = self._items.get(key)
        if existing is not None:
            raise ValueError("Artifact IDs must be unique per run")
        decision = self._decision(artifact.artifact_id)
        if decision["drop"]:
            return
        stored = artifact
        if decision["corrupt"]:
            stored = Artifact(
                spec_version=artifact.spec_version,
                artifact_id=artifact.artifact_id,
                tenant_id=artifact.tenant_id,
                artifact_type=artifact.artifact_type,
                producer=artifact.producer,
                parent_artifacts=artifact.parent_artifacts,
                content_hash=ContentHash(
                    self._hash_payload(f"corrupt:{artifact.content_hash}")
                ),
                scope=artifact.scope,
            )
        if decision["delay"] > 0:
            self._pending[key] = (stored, decision["delay"])
            return
        self._items[key] = stored

    def load(self, artifact_id: ArtifactID, *, tenant_id: TenantID) -> Artifact:
        """Execute load and enforce its contract."""
        self._tick()
        key = (tenant_id, artifact_id)
        if key in self._pending:
            artifact, delay = self._pending[key]
            if delay > 0:
                self._pending[key] = (artifact, delay - 1)
                raise KeyError(f"Artifact not yet visible: {artifact_id}")
            self._items[key] = artifact
            self._pending.pop(key, None)
        if key not in self._items:
            raise KeyError(f"Artifact not found: {artifact_id}")
        return self._items[key]

    def _tick(self) -> None:
        """Internal helper; not part of the public API."""
        for key, (artifact, delay) in list(self._pending.items()):
            if delay <= 0:
                self._items[key] = artifact
                self._pending.pop(key, None)

    def _decision(self, artifact_id: ArtifactID) -> dict[str, object]:
        """Internal helper; not part of the public API."""
        payload = f"{self._seed}:{artifact_id}"
        digest = self._hash_payload(payload)
        bucket = int(digest[:8], 16) % 100
        drop = bucket < int(self._drop_rate * 100)
        corrupt = not drop and bucket < int(self._drop_rate * 100) + int(
            self._corruption_rate * 100
        )
        delay = 0
        if not drop:
            delay = int(digest[8:16], 16) % (self._max_delay + 1)
        return {"drop": drop, "corrupt": corrupt, "delay": delay}

    @staticmethod
    def _hash_payload(payload: str) -> str:
        """Internal helper; not part of the public API."""
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
