# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Validated results from durable corpus snapshot publication."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

RecoveryStatus = Literal["empty", "healthy", "recovered"]


def _is_identity(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


@dataclass(frozen=True, slots=True)
class PublishedCorpusSnapshot:
    """An admitted generation whose bytes and identity have been verified."""

    snapshot_id: str
    canonical_bytes: bytes
    canonical_sha256: str
    relation_sha256: str | None = None
    source_object_count: int = 0
    derived_object_count: int = 0

    def __post_init__(self) -> None:
        if not _is_identity(self.snapshot_id):
            raise ValueError("published corpus snapshot requires a snapshot identity")
        observed = hashlib.sha256(self.canonical_bytes).hexdigest()
        if observed != self.canonical_sha256:
            raise ValueError(
                "published corpus snapshot bytes do not match their digest"
            )
        if self.relation_sha256 is None:
            if self.source_object_count or self.derived_object_count:
                raise ValueError("legacy publication cannot declare relation objects")
        elif (
            not _is_identity(self.relation_sha256)
            or self.source_object_count <= 0
            or self.derived_object_count <= 0
        ):
            raise ValueError("published corpus relation identity is invalid")

    @property
    def generation_name(self) -> str:
        return self.snapshot_id.removeprefix("sha256:")

    def manifest(self) -> dict[str, object]:
        manifest: dict[str, object] = {
            "byte_length": len(self.canonical_bytes),
            "canonical_sha256": self.canonical_sha256,
            "generation_name": self.generation_name,
            "schema_version": (
                "bijux.canon.ingest.corpus_publication.v1"
                if self.relation_sha256 is None
                else "bijux.canon.ingest.corpus_publication.v2"
            ),
            "snapshot_id": self.snapshot_id,
        }
        if self.relation_sha256 is not None:
            manifest.update(
                {
                    "derived_object_count": self.derived_object_count,
                    "relation_sha256": self.relation_sha256,
                    "source_object_count": self.source_object_count,
                }
            )
        return manifest


@dataclass(frozen=True, slots=True)
class SnapshotRecovery:
    """The admitted generation selected while reconciling durable state."""

    status: RecoveryStatus
    snapshot: PublishedCorpusSnapshot | None
    removed_staging_entries: int

    def __post_init__(self) -> None:
        if self.status not in {"empty", "healthy", "recovered"}:
            raise ValueError("unsupported snapshot recovery status")
        if self.removed_staging_entries < 0:
            raise ValueError("removed staging entry count must not be negative")
        if (self.status == "empty") != (self.snapshot is None):
            raise ValueError("only empty recovery results may omit a snapshot")


__all__ = [
    "PublishedCorpusSnapshot",
    "RecoveryStatus",
    "SnapshotRecovery",
]
