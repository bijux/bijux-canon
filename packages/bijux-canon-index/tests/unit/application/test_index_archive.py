# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for complete portable index generation archives."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexGenerationArchive,
    IndexPreparationCacheStatus,
    IndexQueryChannel,
    IndexQueryRequest,
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


def _build(
    service: IndexService,
    chunks: tuple[AdmittedIndexChunk, ...] | None = None,
) -> str:
    report = service.build(
        _chunks() if chunks is None else chunks,
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


def test_prepared_archive_and_generation_are_reused_across_request_threads(
    tmp_path: Path,
) -> None:
    source = _service(tmp_path / "source")
    archive = source.export(_build(source))
    destination = _service(tmp_path / "destination")

    cold = destination.prepare_archive(archive.canonical_bytes)
    warm = destination.prepare_archive(archive.canonical_bytes)

    assert cold.cache_status is IndexPreparationCacheStatus.cold
    assert warm.cache_status is IndexPreparationCacheStatus.warm
    assert warm.inspection == cold.inspection
    assert destination.resource_cache.report().load_count == 0

    request = IndexQueryRequest(
        channel=IndexQueryChannel.lexical,
        query_text="ancient DNA",
        top_k=1,
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        reports = tuple(
            executor.map(lambda _ordinal: destination.query(request), range(8))
        )

    assert {report.hits[0].chunk_id for report in reports} == {"chunk-a"}
    cache = destination.resource_cache.report()
    assert cache.load_count == 1
    assert cache.last_access_status == "warm"
    assert cache.miss_count == 1
    assert cache.hit_count == 7
    assert cache.resident_generation_ids == (cold.inspection.generation_id,)

    changed_chunks = (
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "Bronze Age mobility changed regional ancestry.",
            (0.0, 0.0, 1.0),
            {"source_id": "paper-c", "language": "en"},
        ),
    )
    changed_source = _service(tmp_path / "changed-source")
    changed_archive = changed_source.export(_build(changed_source, changed_chunks))
    changed = destination.prepare_archive(changed_archive.canonical_bytes)

    assert changed.cache_status is IndexPreparationCacheStatus.invalidated
    assert changed.inspection.generation_id != cold.inspection.generation_id
    changed_report = destination.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text="Bronze Age mobility",
            top_k=1,
        )
    )
    assert changed_report.generation_id == changed.inspection.generation_id
    assert changed_report.hits[0].chunk_id == "chunk-c"
    switched_cache = destination.resource_cache.report()
    assert switched_cache.load_count == 2
    assert switched_cache.last_access_status == "cold"
    assert switched_cache.resident_generation_ids == (changed.inspection.generation_id,)

    destination.close()
    restarted = _service(destination.registry_root)
    assert restarted.resource_cache.report().load_count == 0
    restarted_preparation = restarted.prepare_archive(changed_archive.canonical_bytes)
    restarted_report = restarted.query(
        IndexQueryRequest(
            channel=IndexQueryChannel.lexical,
            query_text="Bronze Age mobility",
            top_k=1,
        )
    )
    assert restarted_preparation.cache_status is IndexPreparationCacheStatus.cold
    assert restarted_report.hits[0].chunk_id == "chunk-c"
    assert restarted.resource_cache.report().load_count == 1


def test_generation_cache_identity_is_isolated_by_registry_root(tmp_path: Path) -> None:
    first = _service(tmp_path / "workspace-a" / "indexes")
    second = _service(tmp_path / "workspace-b" / "indexes")

    assert (
        first.resource_cache.report().cache_identity
        != second.resource_cache.report().cache_identity
    )
