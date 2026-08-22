# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for complete portable index generation archives."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexGenerationArchive,
    IndexService,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            "chunk-a",
            "paper-a",
            0,
            "Ancient DNA preserves direct evidence.",
            (1.0, 0.0, 0.0),
            {"source_id": "paper-a", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-b",
            "paper-b",
            0,
            "Genomic contamination constrains interpretation.",
            (0.0, 1.0, 0.0),
            {"source_id": "paper-b", "language": "en"},
        ),
    )


def _service(path: Path) -> IndexService:
    return IndexService(
        path,
        compatibility=IndexCompatibility("sha256:model-lock", 3),
    )


def _build(service: IndexService) -> str:
    report = service.build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8, seed=17),
    )
    return report.generation_id


def test_archive_round_trip_admits_every_generation_file_after_restart(
    tmp_path: Path,
) -> None:
    source = _service(tmp_path / "source")
    generation_id = _build(source)

    archive = source.export(generation_id)
    parsed = IndexGenerationArchive.from_bytes(archive.canonical_bytes)

    assert parsed == archive
    assert [item.name for item in archive.files] == [
        "lexical.sqlite",
        "dense-exact.sqlite",
        "dense-hnsw.sqlite",
        "generation.json",
    ]
    assert all(item.content for item in archive.files)

    destination = _service(tmp_path / "destination")
    admitted = destination.admit_archive(archive.canonical_bytes, activate=True)
    restarted = _service(destination.registry_root)

    assert admitted.generation_id == generation_id
    assert admitted.activation.active is True
    assert restarted.verify().generation_id == generation_id


def test_archive_corruption_fails_before_registry_admission(tmp_path: Path) -> None:
    source = _service(tmp_path / "source")
    archive = source.export(_build(source))
    payload = json.loads(archive.canonical_bytes)
    payload["files"][0]["sha256"] = "0" * 64
    corrupted = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    destination = _service(tmp_path / "destination")

    with pytest.raises(ValueError, match="invalid"):
        destination.admit_archive(corrupted)

    assert not tuple((destination.registry_root / "generations").iterdir())
