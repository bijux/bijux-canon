# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for immutable incremental index mutation."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexDelta,
    IndexGeneration,
    apply_index_delta,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


def _chunk(identity: str, vector: tuple[float, ...], text: str) -> AdmittedIndexChunk:
    return AdmittedIndexChunk(
        chunk_id=identity,
        document_id=f"document-{identity}",
        ordinal=0,
        text=text,
        vector=vector,
        metadata={"source_id": f"source-{identity}", "language": "en"},
    )


def _base() -> tuple[AdmittedIndexChunk, ...]:
    return (
        _chunk("chunk-a", (1.0, 0.0, 0.0), "Ancient DNA alpha evidence"),
        _chunk("chunk-b", (0.0, 1.0, 0.0), "Ancient DNA beta evidence"),
        _chunk("chunk-c", (0.0, 0.0, 1.0), "Ancient DNA gamma evidence"),
    )


def _limits() -> IndexBuildLimits:
    return IndexBuildLimits(20, 20_000, 20_000, 20_000)


def _parameters() -> HnswParameters:
    return HnswParameters(m=2, ef_construction=8, ef_search=8, seed=11)


def _parent(path: Path) -> IndexGeneration:
    return IndexGeneration.build(
        path,
        _base(),
        snapshot_artifact_id="sha256:snapshot-a",
        model_lock_artifact_id="sha256:model",
        limits=_limits(),
        hnsw_parameters=_parameters(),
    )


def _delta() -> IndexDelta:
    return IndexDelta(
        additions=(_chunk("chunk-d", (0.5, 0.5, 0.0), "Ancient DNA delta evidence"),),
        modifications=(
            _chunk("chunk-a", (0.0, 1.0, 0.0), "Ancient DNA alpha revised"),
        ),
        deletions=("chunk-b",),
        tombstones=("chunk-c",),
    )


def test_delta_matches_clean_rebuild_and_preserves_parent(tmp_path: Path) -> None:
    with _parent(tmp_path / "parent") as parent:
        parent_id = parent.manifest.generation_id
        derived, receipt = apply_index_delta(
            parent,
            tmp_path / "derived",
            _delta(),
            snapshot_artifact_id="sha256:snapshot-b",
            limits=_limits(),
        )
        with derived:
            admitted = derived.admitted_chunks()
            lineage = derived.manifest.lineage
            derived_manifest = derived.manifest
            assert [chunk.chunk_id for chunk in admitted] == ["chunk-a", "chunk-d"]
            assert next(
                chunk for chunk in admitted if chunk.chunk_id == "chunk-a"
            ).text == ("Ancient DNA alpha revised")
            assert receipt.parent_generation_id == parent_id
            assert (
                receipt.added,
                receipt.modified,
                receipt.deleted,
                receipt.tombstoned,
            ) == (
                1,
                1,
                1,
                1,
            )
        with IndexGeneration.build(
            tmp_path / "clean",
            admitted,
            snapshot_artifact_id="sha256:snapshot-b",
            model_lock_artifact_id="sha256:model",
            limits=_limits(),
            hnsw_parameters=_parameters(),
            lineage=lineage,
        ) as clean:
            assert clean.manifest == derived_manifest
        assert parent.manifest.generation_id == parent_id
        assert [chunk.chunk_id for chunk in parent.admitted_chunks()] == [
            "chunk-a",
            "chunk-b",
            "chunk-c",
        ]

    with IndexGeneration.open(tmp_path / "derived") as restarted:
        assert restarted.manifest == derived_manifest


def test_modified_vectors_replace_parent_embedding(tmp_path: Path) -> None:
    with _parent(tmp_path / "parent") as parent:
        before = {
            result.chunk_id: result.score
            for result in parent.exact.query((1.0, 0.0, 0.0))
        }
        derived, _ = apply_index_delta(
            parent,
            tmp_path / "derived",
            IndexDelta(
                modifications=(
                    _chunk("chunk-a", (0.0, 0.0, 1.0), "Ancient DNA alpha re-embedded"),
                )
            ),
            snapshot_artifact_id="sha256:snapshot-b",
            limits=_limits(),
        )
        with derived:
            after = {
                result.chunk_id: result.score
                for result in derived.exact.query((1.0, 0.0, 0.0))
            }

    assert before["chunk-a"] == pytest.approx(1.0)
    assert after["chunk-a"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("delta", "message"),
    [
        (IndexDelta(additions=(_base()[0],)), "already exist"),
        (
            IndexDelta(modifications=(_chunk("missing", (1.0, 0.0, 0.0), "x"),)),
            "must exist",
        ),
        (IndexDelta(deletions=("missing",)), "must exist"),
    ],
)
def test_invalid_parent_transitions_publish_nothing(
    tmp_path: Path, delta: IndexDelta, message: str
) -> None:
    destination = tmp_path / "derived"
    with _parent(tmp_path / "parent") as parent:
        with pytest.raises(ValueError, match=message):
            apply_index_delta(
                parent,
                destination,
                delta,
                snapshot_artifact_id="sha256:snapshot-b",
                limits=_limits(),
            )
    assert not destination.exists()


def test_delta_categories_reject_overlap_and_duplicate_payloads() -> None:
    with pytest.raises(ValueError, match="overlap"):
        IndexDelta(additions=(_base()[0],), deletions=("chunk-a",))
    with pytest.raises(ValueError, match="unique"):
        IndexDelta(additions=(_base()[0], _base()[0]))
    with pytest.raises(ValueError, match="unique"):
        IndexDelta(deletions=("chunk-a", "chunk-a"))
    with pytest.raises(ValueError, match="must not be empty"):
        IndexDelta()
