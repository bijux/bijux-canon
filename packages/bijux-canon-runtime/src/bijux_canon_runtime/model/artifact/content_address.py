# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Schema-bound content identity for immutable Runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from bijux_canon_runtime.ontology.ids import ArtifactID, ContentHash


_ARTIFACT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_SCHEMA_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_LOGICAL_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    """Encode strict JSON values into deterministic UTF-8 bytes."""
    _validate_json(payload, path="$", seen=set())
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _validate_json(payload: Any, *, path: str, seen: set[int]) -> None:
    if payload is None or isinstance(payload, str | bool | int):
        return
    if isinstance(payload, float):
        if payload != payload or payload in (float("inf"), float("-inf")):
            raise ValueError(f"non-finite number at {path}")
        return
    if isinstance(payload, dict):
        identity = id(payload)
        if identity in seen:
            raise ValueError(f"cyclic JSON object at {path}")
        seen.add(identity)
        for key, value in payload.items():
            if not isinstance(key, str):
                raise TypeError(f"JSON object key at {path} must be a string")
            _validate_json(value, path=f"{path}.{key}", seen=seen)
        seen.remove(identity)
        return
    if isinstance(payload, list):
        identity = id(payload)
        if identity in seen:
            raise ValueError(f"cyclic JSON array at {path}")
        seen.add(identity)
        for index, value in enumerate(payload):
            _validate_json(value, path=f"{path}[{index}]", seen=seen)
        seen.remove(identity)
        return
    raise TypeError(f"unsupported JSON value at {path}: {type(payload).__name__}")


@dataclass(frozen=True, slots=True)
class ImmutableArtifactDescriptor:
    """Integrity and provenance metadata for one immutable blob."""

    artifact_id: ArtifactID
    schema_id: str
    media_type: str
    size_bytes: int
    payload_sha256: ContentHash
    producer: str
    dependencies: tuple[ArtifactID, ...]

    def __post_init__(self) -> None:
        if not _ARTIFACT_ID.fullmatch(str(self.artifact_id)):
            raise ValueError("immutable artifact_id must be a SHA-256 artifact ID")
        if not _SCHEMA_ID.fullmatch(self.schema_id):
            raise ValueError("schema_id has an invalid format")
        if "/" not in self.media_type or any(char.isspace() for char in self.media_type):
            raise ValueError("media_type must be a concrete MIME type")
        if self.size_bytes < 0:
            raise ValueError("artifact size must not be negative")
        if not re.fullmatch(r"[0-9a-f]{64}", str(self.payload_sha256)):
            raise ValueError("payload_sha256 must be a SHA-256 digest")
        if not self.producer.strip():
            raise ValueError("artifact producer must not be empty")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("artifact dependencies must be unique")
        if tuple(sorted(self.dependencies)) != self.dependencies:
            raise ValueError("artifact dependencies must be sorted")
        if any(not _ARTIFACT_ID.fullmatch(str(item)) for item in self.dependencies):
            raise ValueError("artifact dependencies must be immutable artifact IDs")
        if self.artifact_id in self.dependencies:
            raise ValueError("an artifact cannot depend on itself")


@dataclass(frozen=True, slots=True)
class AddressedArtifact:
    """Canonical payload bytes paired with their verified descriptor."""

    descriptor: ImmutableArtifactDescriptor
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        expected = describe_artifact(
            canonical_bytes=self.canonical_bytes,
            schema_id=self.descriptor.schema_id,
            media_type=self.descriptor.media_type,
            producer=self.descriptor.producer,
            dependencies=self.descriptor.dependencies,
        )
        if expected != self.descriptor:
            raise ValueError("artifact descriptor does not match canonical payload bytes")

    @classmethod
    def from_json(
        cls,
        payload: Any,
        *,
        schema_id: str,
        producer: str,
        dependencies: tuple[ArtifactID, ...] = (),
    ) -> AddressedArtifact:
        """Address a strict JSON payload using its canonical representation."""
        canonical = canonical_json_bytes(payload)
        descriptor = describe_artifact(
            canonical_bytes=canonical,
            schema_id=schema_id,
            media_type="application/json",
            producer=producer,
            dependencies=dependencies,
        )
        return cls(descriptor=descriptor, canonical_bytes=canonical)

    @classmethod
    def from_bytes(
        cls,
        payload: bytes,
        *,
        schema_id: str,
        media_type: str,
        producer: str,
        dependencies: tuple[ArtifactID, ...] = (),
    ) -> AddressedArtifact:
        """Address caller-declared canonical bytes without text coercion."""
        canonical = bytes(payload)
        descriptor = describe_artifact(
            canonical_bytes=canonical,
            schema_id=schema_id,
            media_type=media_type,
            producer=producer,
            dependencies=dependencies,
        )
        return cls(descriptor=descriptor, canonical_bytes=canonical)


def describe_artifact(
    *,
    canonical_bytes: bytes,
    schema_id: str,
    media_type: str,
    producer: str,
    dependencies: tuple[ArtifactID, ...],
) -> ImmutableArtifactDescriptor:
    """Derive identity and complete metadata from canonical payload bytes."""
    if not _SCHEMA_ID.fullmatch(schema_id):
        raise ValueError("schema_id has an invalid format")
    identity_bytes = (
        schema_id.encode("utf-8")
        + b"\0"
        + media_type.encode("ascii")
        + b"\0"
        + canonical_bytes
    )
    return ImmutableArtifactDescriptor(
        artifact_id=ArtifactID("sha256:" + _sha256(identity_bytes)),
        schema_id=schema_id,
        media_type=media_type,
        size_bytes=len(canonical_bytes),
        payload_sha256=ContentHash(_sha256(canonical_bytes)),
        producer=producer,
        dependencies=dependencies,
    )


@dataclass(frozen=True, slots=True)
class LogicalArtifactReference:
    """Versioned mutable name resolving to an immutable blob identity."""

    logical_id: str
    namespace: str
    name: str
    revision: int
    target_artifact_id: ArtifactID

    @classmethod
    def create(
        cls,
        *,
        namespace: str,
        name: str,
        revision: int,
        target_artifact_id: ArtifactID,
    ) -> LogicalArtifactReference:
        if not _LOGICAL_PART.fullmatch(namespace) or not _LOGICAL_PART.fullmatch(name):
            raise ValueError("logical reference namespace and name must be stable names")
        if revision < 0:
            raise ValueError("logical reference revision must not be negative")
        if not _ARTIFACT_ID.fullmatch(str(target_artifact_id)):
            raise ValueError("logical reference target must be immutable")
        return cls(
            logical_id=f"logical:{namespace}/{name}",
            namespace=namespace,
            name=name,
            revision=revision,
            target_artifact_id=target_artifact_id,
        )

    def advance(self, target_artifact_id: ArtifactID) -> LogicalArtifactReference:
        """Create the next logical revision without changing prior state."""
        return self.create(
            namespace=self.namespace,
            name=self.name,
            revision=self.revision + 1,
            target_artifact_id=target_artifact_id,
        )


__all__ = [
    "AddressedArtifact",
    "ImmutableArtifactDescriptor",
    "LogicalArtifactReference",
    "canonical_json_bytes",
    "describe_artifact",
]
