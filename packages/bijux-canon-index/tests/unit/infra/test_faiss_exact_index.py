# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.infra.adapters.faiss import (
    DenseVectorRecord,
    FaissExactIndex,
    FaissExactIndexCorruptionError,
)


def _records() -> tuple[DenseVectorRecord, ...]:
    return (
        DenseVectorRecord(
            "chunk-b",
            (0.0, 4.0, 0.0),
            {"document_id": "document-b", "year": 2024, "reviewed": True},
        ),
        DenseVectorRecord(
            "chunk-a",
            (3.0, 0.0, 0.0),
            {"document_id": "document-a", "year": 2023, "reviewed": True},
        ),
        DenseVectorRecord(
            "chunk-c",
            (1.0, 1.0, 0.0),
            {"document_id": "document-c", "year": 2024, "reviewed": False},
        ),
    )


def test_faiss_exact_persists_score_and_mapping_across_restart(
    tmp_path: Path,
) -> None:
    path = tmp_path / "exact.sqlite"
    with FaissExactIndex.build(
        path,
        _records(),
        model_lock_artifact_id="sha256:model-lock",
    ) as built:
        first = built.query((1.0, 0.0, 0.0))
        manifest = built.manifest

    with FaissExactIndex(path) as reopened:
        assert reopened.manifest == manifest
        assert reopened.query((2.0, 0.0, 0.0)) == first

    assert manifest.model_lock_artifact_id == "sha256:model-lock"
    assert manifest.dimension == 3
    assert [result.chunk_id for result in first] == [
        "chunk-a",
        "chunk-c",
        "chunk-b",
    ]
    assert first[0].score == pytest.approx(1.0, abs=1e-7)
    assert first[1].score == pytest.approx(2**-0.5, abs=1e-7)
    assert first[2].score == pytest.approx(0.0, abs=1e-7)


def test_faiss_exact_applies_filters_before_top_k(tmp_path: Path) -> None:
    path = tmp_path / "exact.sqlite"
    with FaissExactIndex.build(
        path,
        _records(),
        model_lock_artifact_id="model",
    ) as index:
        results = index.query((1.0, 0.0, 0.0), top_k=1, filters={"year": 2024})
        reviewed = index.query(
            (1.0, 0.0, 0.0),
            filters={"year": 2024, "reviewed": True},
        )

    assert [result.chunk_id for result in results] == ["chunk-c"]
    assert [result.chunk_id for result in reviewed] == ["chunk-b"]


def test_faiss_exact_generation_is_input_order_independent(tmp_path: Path) -> None:
    with FaissExactIndex.build(
        tmp_path / "forward.sqlite",
        _records(),
        model_lock_artifact_id="model",
    ) as forward:
        forward_manifest = forward.manifest
    with FaissExactIndex.build(
        tmp_path / "reverse.sqlite",
        reversed(_records()),
        model_lock_artifact_id="model",
    ) as reverse:
        reverse_manifest = reverse.manifest

    assert reverse_manifest == forward_manifest


def test_faiss_exact_breaks_score_ties_by_chunk_identity(tmp_path: Path) -> None:
    records = (
        DenseVectorRecord("chunk-z", (1.0, 0.0), {}),
        DenseVectorRecord("chunk-a", (1.0, 0.0), {}),
    )
    with FaissExactIndex.build(
        tmp_path / "exact.sqlite",
        records,
        model_lock_artifact_id="model",
    ) as index:
        results = index.query((1.0, 0.0))

    assert [result.chunk_id for result in results] == ["chunk-a", "chunk-z"]


def test_faiss_exact_detects_index_and_mapping_corruption(tmp_path: Path) -> None:
    index_path = tmp_path / "corrupt-index.sqlite"
    with FaissExactIndex.build(
        index_path,
        _records(),
        model_lock_artifact_id="model",
    ):
        pass
    with sqlite3.connect(index_path) as connection:
        connection.execute(
            "UPDATE dense_index SET serialized_index=? WHERE singleton=1",
            (b"not-faiss",),
        )
    with pytest.raises(FaissExactIndexCorruptionError, match="checksum"):
        FaissExactIndex(index_path)

    mapping_path = tmp_path / "corrupt-mapping.sqlite"
    with FaissExactIndex.build(
        mapping_path,
        _records(),
        model_lock_artifact_id="model",
    ):
        pass
    with sqlite3.connect(mapping_path) as connection:
        connection.execute(
            "UPDATE dense_records SET chunk_id='tampered' WHERE position=0"
        )
    with pytest.raises(FaissExactIndexCorruptionError, match="identity"):
        FaissExactIndex(mapping_path)


def test_faiss_exact_failed_replacement_preserves_active_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "exact.sqlite"
    with FaissExactIndex.build(
        path,
        _records(),
        model_lock_artifact_id="model",
    ) as index:
        generation_id = index.manifest.generation_id

    def reject_publication(
        _source: os.PathLike[str], _target: os.PathLike[str]
    ) -> None:
        raise OSError("injected atomic publication failure")

    monkeypatch.setattr(os, "replace", reject_publication)
    with pytest.raises(OSError, match="publication failure"):
        FaissExactIndex.build(
            path,
            _records()[:2],
            model_lock_artifact_id="model",
            replace=True,
        )
    with FaissExactIndex(path) as reopened:
        assert reopened.manifest.generation_id == generation_id


def test_faiss_exact_rejects_invalid_vectors_and_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one"):
        FaissExactIndex.build(
            tmp_path / "empty.sqlite",
            (),
            model_lock_artifact_id="model",
        )
    with pytest.raises(ValueError, match="finite"):
        DenseVectorRecord("chunk", (float("nan"),), {})
    with pytest.raises(ValueError, match="same dimension"):
        FaissExactIndex.build(
            tmp_path / "dimensions.sqlite",
            (
                DenseVectorRecord("a", (1.0,), {}),
                DenseVectorRecord("b", (1.0, 0.0), {}),
            ),
            model_lock_artifact_id="model",
        )

    with FaissExactIndex.build(
        tmp_path / "exact.sqlite",
        _records(),
        model_lock_artifact_id="model",
    ) as index:
        with pytest.raises(ValueError, match="non-zero norm"):
            index.query((0.0, 0.0, 0.0))
        with pytest.raises(ValueError, match="dimension"):
            index.query((1.0, 0.0))
        with pytest.raises(ValueError, match="top_k"):
            index.query((1.0, 0.0, 0.0), top_k=0)
