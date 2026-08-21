# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for complete index integrity and compatibility audits."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexCompatibility,
    IndexBuildLimits,
    IndexGeneration,
    IndexGenerationIncompatibleError,
    IndexGenerationRegistry,
    audit_index_generation,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _build(path: Path, identity: str) -> IndexGeneration:
    return IndexGeneration.build(
        path,
        (
            AdmittedIndexChunk(
                f"chunk-{identity}",
                f"document-{identity}",
                0,
                f"Ancient DNA evidence {identity}",
                (1.0, 0.0, 0.0),
                {"source_id": f"source-{identity}"},
            ),
        ),
        snapshot_artifact_id=f"sha256:snapshot-{identity}",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8),
    )


def test_audit_closes_every_generation_integrity_surface(tmp_path: Path) -> None:
    with _build(tmp_path / "generation", "a") as generation:
        report = audit_index_generation(
            generation.path,
            compatibility=IndexCompatibility("sha256:model", 3),
        )

    assert report.generation_id == generation.manifest.generation_id
    assert report.chunk_count == 1
    assert set(report.checks) == {
        "canonical_generation_manifest",
        "segment_file_hashes",
        "backend_schema_runtime_identity",
        "model_lock_consistency",
        "chunk_mapping_uniqueness",
        "cross_segment_chunk_reachability",
        "stored_content_tamper_detection",
    }


@pytest.mark.parametrize(
    "compatibility",
    [IndexCompatibility("sha256:other-model", 3), IndexCompatibility("sha256:model", 4)],
)
def test_incompatible_model_profile_is_refused(
    tmp_path: Path, compatibility: IndexCompatibility
) -> None:
    with _build(tmp_path / "generation", "a") as generation:
        with pytest.raises(IndexGenerationIncompatibleError, match="incompatible"):
            audit_index_generation(generation.path, compatibility=compatibility)


def test_registry_refuses_incompatible_generation_before_admission(
    tmp_path: Path,
) -> None:
    registry = IndexGenerationRegistry(
        tmp_path / "registry",
        compatibility=IndexCompatibility("sha256:other-model", 3),
    )
    with _build(tmp_path / "generation", "a") as generation:
        with pytest.raises(IndexGenerationIncompatibleError, match="model lock"):
            registry.admit(generation.path)

    assert list(registry.generations.iterdir()) == []


def test_segment_tamper_is_refused_before_admission(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    with _build(tmp_path / "generation", "a") as generation:
        path = generation.path
    segment = path / "dense-exact.sqlite"
    with segment.open("r+b") as handle:
        handle.seek(-1, 2)
        original = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([original[0] ^ 0xFF]))

    with pytest.raises(ValueError, match="segment hash mismatch"):
        registry.admit(path)
    assert list(registry.generations.iterdir()) == []
