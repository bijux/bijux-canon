# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Clean-room replay contract for persistent index generations."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexQueryChannel,
    IndexQueryRequest,
    IndexService,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters

HNSW_SCORE_ABSOLUTE_TOLERANCE = 2e-6


def _chunks() -> tuple[AdmittedIndexChunk, ...]:
    return (
        AdmittedIndexChunk(
            "chunk-a",
            "paper-a",
            0,
            "Ancient DNA preserves direct evidence.",
            (1.0, 0.0, 0.0, 0.0),
            {"source_id": "paper-a", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-b",
            "paper-b",
            0,
            "Genomic contamination constrains interpretation.",
            (0.7, 0.7, 0.0, 0.0),
            {"source_id": "paper-b", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-c",
            "paper-c",
            0,
            "Proteomic evidence survives in mineralized tissue.",
            (0.0, 1.0, 0.0, 0.0),
            {"source_id": "paper-c", "language": "en"},
        ),
        AdmittedIndexChunk(
            "chunk-d",
            "paper-d",
            0,
            "Stratigraphic context bounds archaeological interpretation.",
            (0.0, 0.0, 1.0, 0.0),
            {"source_id": "paper-d", "language": "en"},
        ),
    )


def _build(root: Path) -> IndexService:
    service = IndexService(
        root,
        compatibility=IndexCompatibility("sha256:model-lock", 4),
    )
    service.build(
        _chunks(),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model-lock",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(
            m=2,
            ef_construction=8,
            ef_search=8,
            seed=17,
        ),
        activate=True,
    )
    return service


def _query(
    service: IndexService, channel: IndexQueryChannel
) -> tuple[tuple[str, float], ...]:
    report = service.query(
        IndexQueryRequest(
            channel=channel,
            query_vector=(1.0, 0.1, 0.0, 0.0),
            top_k=4,
        )
    )
    return tuple((hit.chunk_id, hit.score) for hit in report.hits)


def test_locked_inputs_rebuild_with_equal_semantic_identity(tmp_path: Path) -> None:
    first = _build(tmp_path / "first-registry")
    second = _build(tmp_path / "second-registry")

    first_report = first.inspect()
    second_report = second.inspect()
    assert first_report == second_report


def test_exact_and_ann_results_respect_replay_boundaries(tmp_path: Path) -> None:
    first = _build(tmp_path / "first-registry")
    second = _build(tmp_path / "second-registry")

    assert _query(first, IndexQueryChannel.dense_exact) == _query(
        second, IndexQueryChannel.dense_exact
    )
    first_ann = _query(first, IndexQueryChannel.dense_hnsw)
    second_ann = _query(second, IndexQueryChannel.dense_hnsw)
    assert [chunk_id for chunk_id, _ in first_ann] == [
        chunk_id for chunk_id, _ in second_ann
    ]
    assert all(
        abs(first_score - second_score) <= HNSW_SCORE_ABSOLUTE_TOLERANCE
        for (_, first_score), (_, second_score) in zip(
            first_ann, second_ann, strict=True
        )
    )

    restarted = IndexService(
        second.registry_root,
        compatibility=IndexCompatibility("sha256:model-lock", 4),
    )
    assert _query(restarted, IndexQueryChannel.dense_exact) == _query(
        second, IndexQueryChannel.dense_exact
    )
