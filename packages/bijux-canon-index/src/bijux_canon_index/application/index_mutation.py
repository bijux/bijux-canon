# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Derive immutable index generations from admitted snapshot deltas."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from bijux_canon_index.application.index_generation import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexGeneration,
    IndexGenerationLineage,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _chunk_payload(chunk: AdmittedIndexChunk) -> dict[str, object]:
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "metadata": dict(chunk.metadata),
        "ordinal": chunk.ordinal,
        "text": chunk.text,
        "vector": [float(value) for value in chunk.vector],
    }


@dataclass(frozen=True, slots=True)
class IndexDelta:
    """One complete add/modify/delete/tombstone snapshot transition."""

    additions: tuple[AdmittedIndexChunk, ...] = ()
    modifications: tuple[AdmittedIndexChunk, ...] = ()
    deletions: tuple[str, ...] = ()
    tombstones: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        additions = tuple(sorted(self.additions, key=lambda chunk: chunk.chunk_id))
        modifications = tuple(
            sorted(self.modifications, key=lambda chunk: chunk.chunk_id)
        )
        if len(self.deletions) != len(set(self.deletions)) or len(
            self.tombstones
        ) != len(set(self.tombstones)):
            raise ValueError("index delta categories require unique chunk identities")
        deletions = tuple(sorted(set(self.deletions)))
        tombstones = tuple(sorted(set(self.tombstones)))
        if any(not chunk_id for chunk_id in (*deletions, *tombstones)):
            raise ValueError("index delta removals require non-empty chunk identities")
        categories = (
            [chunk.chunk_id for chunk in additions],
            [chunk.chunk_id for chunk in modifications],
            list(deletions),
            list(tombstones),
        )
        if any(len(values) != len(set(values)) for values in categories):
            raise ValueError("index delta categories require unique chunk identities")
        flattened = [chunk_id for values in categories for chunk_id in values]
        if len(flattened) != len(set(flattened)):
            raise ValueError("index delta categories must not overlap")
        if not flattened:
            raise ValueError("index delta must not be empty")
        object.__setattr__(self, "additions", additions)
        object.__setattr__(self, "modifications", modifications)
        object.__setattr__(self, "deletions", deletions)
        object.__setattr__(self, "tombstones", tombstones)

    @property
    def sha256(self) -> str:
        """Return the content identity of the complete canonical delta."""

        payload = {
            "additions": [_chunk_payload(chunk) for chunk in self.additions],
            "deletions": list(self.deletions),
            "modifications": [
                _chunk_payload(chunk) for chunk in self.modifications
            ],
            "schema_version": "bijux.canon.index.delta.v1",
            "tombstones": list(self.tombstones),
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class IndexMutationReceipt:
    """Stable summary of an admitted immutable generation transition."""

    parent_generation_id: str
    generation_id: str
    previous_snapshot_artifact_id: str
    snapshot_artifact_id: str
    delta_sha256: str
    previous_chunk_count: int
    chunk_count: int
    added: int
    modified: int
    deleted: int
    tombstoned: int


def apply_index_delta(
    previous: IndexGeneration,
    destination: str | Path,
    delta: IndexDelta,
    *,
    snapshot_artifact_id: str,
    limits: IndexBuildLimits,
    hnsw_parameters: HnswParameters | None = None,
) -> tuple[IndexGeneration, IndexMutationReceipt]:
    """Apply a validated delta and atomically publish a derived generation."""

    if not snapshot_artifact_id:
        raise ValueError("index mutation requires a snapshot identity")
    if snapshot_artifact_id == previous.manifest.snapshot_artifact_id:
        raise ValueError("index mutation requires a new snapshot identity")
    current = {chunk.chunk_id: chunk for chunk in previous.admitted_chunks()}
    additions = {chunk.chunk_id: chunk for chunk in delta.additions}
    modifications = {chunk.chunk_id: chunk for chunk in delta.modifications}
    removals = {*delta.deletions, *delta.tombstones}
    existing = set(current)
    if existing & set(additions):
        raise ValueError("index delta additions already exist in the parent generation")
    if not set(modifications).issubset(existing):
        raise ValueError("index delta modifications must exist in the parent generation")
    if not removals.issubset(existing):
        raise ValueError("index delta removals must exist in the parent generation")
    for chunk_id in removals:
        del current[chunk_id]
    current.update(modifications)
    current.update(additions)
    if not current:
        raise ValueError("index mutation cannot produce an empty generation")
    lineage = IndexGenerationLineage(
        parent_generation_id=previous.manifest.generation_id,
        delta_sha256=delta.sha256,
        added=len(delta.additions),
        modified=len(delta.modifications),
        deleted=len(delta.deletions),
        tombstoned=len(delta.tombstones),
    )
    generation = IndexGeneration.build(
        destination,
        current.values(),
        snapshot_artifact_id=snapshot_artifact_id,
        model_lock_artifact_id=previous.manifest.model_lock_artifact_id,
        limits=limits,
        hnsw_parameters=hnsw_parameters or previous.manifest.hnsw_parameters,
        lineage=lineage,
    )
    receipt = IndexMutationReceipt(
        parent_generation_id=previous.manifest.generation_id,
        generation_id=generation.manifest.generation_id,
        previous_snapshot_artifact_id=previous.manifest.snapshot_artifact_id,
        snapshot_artifact_id=snapshot_artifact_id,
        delta_sha256=delta.sha256,
        previous_chunk_count=previous.manifest.statistics.chunk_count,
        chunk_count=generation.manifest.statistics.chunk_count,
        added=lineage.added,
        modified=lineage.modified,
        deleted=lineage.deleted,
        tombstoned=lineage.tombstoned,
    )
    if generation.manifest.lineage != lineage:
        generation.close()
        raise ValueError("derived index generation lost its mutation lineage")
    return generation, receipt


__all__ = ["IndexDelta", "IndexMutationReceipt", "apply_index_delta"]
