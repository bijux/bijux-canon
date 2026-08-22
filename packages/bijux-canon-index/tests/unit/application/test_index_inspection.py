# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for content-safe immutable index inspection."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexActivationError,
    IndexBuildLimits,
    IndexCompatibility,
    IndexDelta,
    IndexGeneration,
    IndexGenerationIncompatibleError,
    IndexGenerationRegistry,
    apply_index_delta,
    inspect_index_generation,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunk(identity: str, vector: tuple[float, ...]) -> AdmittedIndexChunk:
    return AdmittedIndexChunk(
        chunk_id=f"chunk-{identity}",
        document_id=f"document-{identity}",
        ordinal=0,
        text=f"sensitive exact source text {identity}",
        vector=vector,
        metadata={
            "source_id": f"private-source-{identity}",
            "language": "en",
            "operator_secret": "must-not-leak",
        },
    )


def _limits() -> IndexBuildLimits:
    return IndexBuildLimits(10, 10_000, 10_000, 10_000)


def _build(path: Path) -> IndexGeneration:
    return IndexGeneration.build(
        path,
        (
            _chunk("a", (1.0, 0.0, 0.0)),
            _chunk("b", (0.0, 1.0, 0.0)),
            _chunk("c", (0.0, 0.0, 1.0)),
        ),
        snapshot_artifact_id="sha256:corpus-snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=_limits(),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=13),
    )


def test_registry_inspection_reports_active_derived_generation(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(
        tmp_path / "registry",
        compatibility=IndexCompatibility("sha256:model-lock", 3),
    )
    with _build(tmp_path / "parent") as parent:
        parent_id = parent.manifest.generation_id
        derived, _ = apply_index_delta(
            parent,
            tmp_path / "derived",
            IndexDelta(
                additions=(_chunk("d", (0.5, 0.5, 0.0)),),
                modifications=(_chunk("a", (0.5, 0.0, 0.5)),),
                deletions=("chunk-b",),
                tombstones=("chunk-c",),
            ),
            snapshot_artifact_id="sha256:corpus-snapshot-derived",
            limits=_limits(),
        )
        with derived:
            generation_id = registry.admit(derived.path)
    registry.activate(generation_id)

    report = registry.inspect()

    assert report.generation_id == generation_id
    assert report.snapshot_artifact_id == "sha256:corpus-snapshot-derived"
    assert report.model_lock_artifact_id == "sha256:model-lock"
    assert (report.chunk_count, report.dimension) == (2, 3)
    assert {segment.backend for segment in report.segments} == {
        "sqlite-fts5",
        "faiss-flat-ip",
        "faiss-hnsw",
    }
    assert all(segment.item_count == 2 for segment in report.segments)
    assert all(segment.size_bytes > 0 for segment in report.segments)
    assert all(len(segment.file_sha256) == 64 for segment in report.segments)
    assert report.filters.applied_at_query_time is True
    assert report.filters.value_payloads_exposed is False
    assert "source_id" in report.filters.governed_fields
    assert "contains" in report.filters.operators
    assert report.lineage.parent_generation_id == parent_id
    assert (
        report.lineage.added,
        report.lineage.modified,
        report.lineage.deleted,
        report.lineage.tombstoned,
    ) == (1, 1, 1, 1)
    assert report.integrity.status == "verified"
    assert "segment_file_hashes" in report.integrity.checks
    assert report.activation.active is True
    assert report.activation.active_generation_id == generation_id
    assert report.compatibility.status == "compatible"

    restarted_registry = IndexGenerationRegistry(
        registry.root,
        compatibility=IndexCompatibility("sha256:model-lock", 3),
    )
    assert restarted_registry.inspect() == report


def test_inspection_exposes_no_content_metadata_values_secrets_or_paths(
    tmp_path: Path,
) -> None:
    with _build(tmp_path / "generation") as generation:
        report = inspect_index_generation(generation.path)

    rendered = json.dumps(asdict(report), sort_keys=True)
    assert "sensitive exact source text" not in rendered
    assert "private-source" not in rendered
    assert "operator_secret" not in rendered
    assert "must-not-leak" not in rendered
    assert str(tmp_path) not in rendered
    assert report.compatibility.status == "not_requested"


def test_registry_can_inspect_an_inactive_retained_generation(tmp_path: Path) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")
    with _build(tmp_path / "generation") as generation:
        generation_id = registry.admit(generation.path)

    report = registry.inspect(generation_id)

    assert report.generation_id == generation_id
    assert report.activation.active is False
    assert report.activation.active_generation_id is None


def test_registry_refuses_inspection_without_an_admitted_generation(
    tmp_path: Path,
) -> None:
    registry = IndexGenerationRegistry(tmp_path / "registry")

    with pytest.raises(IndexActivationError, match="available to inspect"):
        registry.inspect()


def test_inspection_refuses_incompatible_or_corrupt_generations(tmp_path: Path) -> None:
    with _build(tmp_path / "generation") as generation:
        path = generation.path
    with pytest.raises(IndexGenerationIncompatibleError, match="incompatible"):
        inspect_index_generation(
            path,
            compatibility=IndexCompatibility("sha256:wrong-model", 3),
        )

    segment = path / "dense-exact.sqlite"
    with segment.open("r+b") as handle:
        handle.seek(-1, 2)
        original = handle.read(1)
        handle.seek(-1, 2)
        handle.write(bytes([original[0] ^ 0xFF]))
    with pytest.raises(ValueError, match="segment hash mismatch"):
        inspect_index_generation(path)
