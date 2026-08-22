# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic corpus deltas, tombstones, and invalidation plans."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Literal

TombstoneReason = Literal["deleted", "modified"]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _is_identity(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True, slots=True)
class SourceTombstone:
    """The immutable old artifact lineage removed by delete or modification."""

    root_name: str
    relative_path: str
    location_id: str
    content_sha256: str
    document_id: str
    chunk_ids: tuple[str, ...]
    reason: TombstoneReason

    def __post_init__(self) -> None:
        if not self.root_name or not self.relative_path:
            raise ValueError("source tombstone requires a stable location")
        if not _is_identity(self.location_id) or not _is_identity(self.document_id):
            raise ValueError(
                "source tombstone requires location and document identities"
            )
        if not _is_sha256(self.content_sha256):
            raise ValueError("source tombstone requires a lowercase content SHA-256")
        if not self.chunk_ids or any(
            not _is_identity(value) for value in self.chunk_ids
        ):
            raise ValueError("source tombstone requires chunk identities")
        if self.chunk_ids != tuple(sorted(set(self.chunk_ids))):
            raise ValueError(
                "source tombstone chunk identities must be unique and ordered"
            )
        if self.reason not in {"deleted", "modified"}:
            raise ValueError("unsupported source tombstone reason")

    def manifest(self) -> dict[str, object]:
        return {
            "chunk_ids": list(self.chunk_ids),
            "content_sha256": self.content_sha256,
            "document_id": self.document_id,
            "location_id": self.location_id,
            "reason": self.reason,
            "relative_path": self.relative_path,
            "root_name": self.root_name,
        }


@dataclass(frozen=True, slots=True)
class SourceRename:
    """A location change whose content-derived artifacts remain identical."""

    previous_location_id: str
    current_location_id: str
    previous_relative_path: str
    current_relative_path: str
    content_sha256: str
    previous_document_id: str
    current_document_id: str

    def __post_init__(self) -> None:
        if self.previous_location_id == self.current_location_id:
            raise ValueError("source rename locations must differ")
        if not all(
            _is_identity(value)
            for value in (
                self.previous_location_id,
                self.current_location_id,
                self.previous_document_id,
                self.current_document_id,
            )
        ):
            raise ValueError("source rename requires stable artifact identities")
        if not self.previous_relative_path or not self.current_relative_path:
            raise ValueError("source rename requires both relative paths")
        if not _is_sha256(self.content_sha256):
            raise ValueError("source rename requires a lowercase content SHA-256")

    def manifest(self) -> dict[str, str]:
        return {
            "content_sha256": self.content_sha256,
            "current_location_id": self.current_location_id,
            "current_relative_path": self.current_relative_path,
            "current_document_id": self.current_document_id,
            "previous_location_id": self.previous_location_id,
            "previous_document_id": self.previous_document_id,
            "previous_relative_path": self.previous_relative_path,
        }


@dataclass(frozen=True, slots=True)
class SourceModification:
    """A stable location whose source or derived artifact identity changed."""

    location_id: str
    relative_path: str
    previous_content_sha256: str
    current_content_sha256: str
    previous_document_id: str
    current_document_id: str

    def __post_init__(self) -> None:
        if not _is_identity(self.location_id) or not all(
            _is_identity(value)
            for value in (self.previous_document_id, self.current_document_id)
        ):
            raise ValueError("source modification requires stable artifact identities")
        if not self.relative_path or not all(
            _is_sha256(value)
            for value in (
                self.previous_content_sha256,
                self.current_content_sha256,
            )
        ):
            raise ValueError("source modification requires path and content identities")

    def manifest(self) -> dict[str, str]:
        return {
            "current_content_sha256": self.current_content_sha256,
            "current_document_id": self.current_document_id,
            "location_id": self.location_id,
            "previous_content_sha256": self.previous_content_sha256,
            "previous_document_id": self.previous_document_id,
            "relative_path": self.relative_path,
        }


@dataclass(frozen=True, slots=True)
class CorpusDelta:
    """A complete deterministic transition between two corpus snapshots."""

    previous_snapshot_id: str
    current_snapshot_id: str
    added_document_ids: tuple[str, ...]
    deleted_document_ids: tuple[str, ...]
    modifications: tuple[SourceModification, ...]
    renames: tuple[SourceRename, ...]
    tombstones: tuple[SourceTombstone, ...]
    added_chunk_ids: tuple[str, ...]
    invalidated_chunk_ids: tuple[str, ...]
    added_rejection_ids: tuple[str, ...]
    removed_rejection_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _is_identity(self.previous_snapshot_id) or not _is_identity(
            self.current_snapshot_id
        ):
            raise ValueError("corpus delta requires snapshot identities")
        identity_lists = (
            self.added_document_ids,
            self.deleted_document_ids,
            self.added_chunk_ids,
            self.invalidated_chunk_ids,
            self.added_rejection_ids,
            self.removed_rejection_ids,
        )
        if any(
            values != tuple(sorted(set(values)))
            or any(not _is_identity(value) for value in values)
            for values in identity_lists
        ):
            raise ValueError("corpus delta identity sets must be unique and ordered")
        if list(self.modifications) != sorted(
            self.modifications, key=lambda item: item.location_id
        ) or list(self.renames) != sorted(
            self.renames,
            key=lambda item: (item.previous_location_id, item.current_location_id),
        ):
            raise ValueError("corpus delta changes must use canonical order")
        if list(self.tombstones) != sorted(
            self.tombstones, key=lambda item: (item.location_id, item.reason)
        ):
            raise ValueError("corpus delta tombstones must use canonical order")

    @property
    def delta_id(self) -> str:
        return _identity(self._payload())

    def _payload(self) -> dict[str, object]:
        return {
            "added_chunk_ids": list(self.added_chunk_ids),
            "added_document_ids": list(self.added_document_ids),
            "added_rejection_ids": list(self.added_rejection_ids),
            "current_snapshot_id": self.current_snapshot_id,
            "deleted_document_ids": list(self.deleted_document_ids),
            "invalidated_chunk_ids": list(self.invalidated_chunk_ids),
            "modifications": [value.manifest() for value in self.modifications],
            "previous_snapshot_id": self.previous_snapshot_id,
            "removed_rejection_ids": list(self.removed_rejection_ids),
            "renames": [value.manifest() for value in self.renames],
            "schema_version": "bijux.canon.ingest.corpus_delta.v1",
            "tombstones": [value.manifest() for value in self.tombstones],
        }

    def manifest(self) -> dict[str, object]:
        payload = self._payload()
        return {"delta_id": _identity(payload), **payload}


__all__ = [
    "CorpusDelta",
    "SourceModification",
    "SourceRename",
    "SourceTombstone",
    "TombstoneReason",
]
