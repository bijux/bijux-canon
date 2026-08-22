# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Complete pre-admission integrity and compatibility audit for index generations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_index.application.index_generation import IndexGeneration


class IndexGenerationIncompatibleError(RuntimeError):
    """A valid generation is incompatible with the selected runtime profile."""


@dataclass(frozen=True, slots=True)
class IndexCompatibility:
    """Runtime requirements that must match a stored generation exactly."""

    model_lock_artifact_id: str
    dimension: int

    def __post_init__(self) -> None:
        if not self.model_lock_artifact_id:
            raise ValueError("index compatibility requires a model lock identity")
        if self.dimension <= 0:
            raise ValueError("index compatibility dimension must be positive")


@dataclass(frozen=True, slots=True)
class IndexGenerationAuditReport:
    """Verified identities and checks completed before use."""

    generation_id: str
    model_lock_artifact_id: str
    dimension: int
    chunk_count: int
    checks: tuple[str, ...]


def audit_index_generation(
    path: str | Path,
    *,
    compatibility: IndexCompatibility | None = None,
) -> IndexGenerationAuditReport:
    """Verify every segment, mapping, runtime identity, and requested lock."""

    with IndexGeneration.open(path) as generation:
        manifest = generation.manifest
        lexical_ids = tuple(chunk.chunk_id for chunk in generation.lexical.chunks())
        exact_ids = tuple(record.chunk_id for record in generation.exact.records())
        hnsw_ids = generation.hnsw.chunk_ids()
        if not (
            lexical_ids == exact_ids == hnsw_ids
            and len(lexical_ids) == len(set(lexical_ids))
            and len(lexical_ids) == manifest.statistics.chunk_count
        ):
            raise IndexGenerationIncompatibleError(
                "index generation chunk mappings are not fully reachable"
            )
        if compatibility is not None:
            if manifest.model_lock_artifact_id != compatibility.model_lock_artifact_id:
                raise IndexGenerationIncompatibleError(
                    "index generation model lock is incompatible"
                )
            if manifest.statistics.dimension != compatibility.dimension:
                raise IndexGenerationIncompatibleError(
                    "index generation vector dimension is incompatible"
                )
        return IndexGenerationAuditReport(
            generation_id=manifest.generation_id,
            model_lock_artifact_id=manifest.model_lock_artifact_id,
            dimension=manifest.statistics.dimension,
            chunk_count=manifest.statistics.chunk_count,
            checks=(
                "canonical_generation_manifest",
                "segment_file_hashes",
                "backend_schema_runtime_identity",
                "model_lock_consistency",
                "chunk_mapping_uniqueness",
                "cross_segment_chunk_reachability",
                "stored_content_tamper_detection",
            ),
        )


__all__ = [
    "IndexCompatibility",
    "IndexGenerationAuditReport",
    "IndexGenerationIncompatibleError",
    "audit_index_generation",
]
