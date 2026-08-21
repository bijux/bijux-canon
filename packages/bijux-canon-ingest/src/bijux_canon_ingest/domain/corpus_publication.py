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

    def __post_init__(self) -> None:
        if not _is_identity(self.snapshot_id):
            raise ValueError("published corpus snapshot requires a snapshot identity")
        observed = hashlib.sha256(self.canonical_bytes).hexdigest()
        if observed != self.canonical_sha256:
            raise ValueError(
                "published corpus snapshot bytes do not match their digest"
            )

    @property
    def generation_name(self) -> str:
        return self.snapshot_id.removeprefix("sha256:")

    def manifest(self) -> dict[str, object]:
        return {
            "byte_length": len(self.canonical_bytes),
            "canonical_sha256": self.canonical_sha256,
            "generation_name": self.generation_name,
            "schema_version": "bijux.canon.ingest.corpus_publication.v1",
            "snapshot_id": self.snapshot_id,
        }


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
