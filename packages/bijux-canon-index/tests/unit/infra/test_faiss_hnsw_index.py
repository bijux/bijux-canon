# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import numpy as np
import pytest

pytest.importorskip("faiss")

from bijux_canon_index.infra.adapters.faiss import (
    DenseVectorRecord,
    FaissExactIndex,
    FaissHnswIndex,
    FaissHnswIndexCorruptionError,
    HnswParameters,
    measure_hnsw_recall,
)


def _records(count: int = 96, dimension: int = 12) -> tuple[DenseVectorRecord, ...]:
    random = np.random.default_rng(20260821)
    vectors = random.normal(size=(count, dimension)).astype("float32")
    return tuple(
        DenseVectorRecord(
            f"chunk-{index:04d}",
            tuple(float(value) for value in vector),
            {"partition": index % 3, "document_id": f"document-{index // 4:04d}"},
        )
        for index, vector in enumerate(vectors)
    )


def test_faiss_hnsw_persists_parameters_mapping_and_results(tmp_path: Path) -> None:
    path = tmp_path / "hnsw.sqlite"
    parameters = HnswParameters(m=16, ef_construction=120, ef_search=64, seed=73)
    with FaissHnswIndex.build(
        path,
        _records(),
        model_lock_artifact_id="sha256:model-lock",
        parameters=parameters,
    ) as built:
        first = built.query(_records()[7].vector, top_k=10)
        manifest = built.manifest

    with FaissHnswIndex(path) as reopened:
        assert reopened.manifest == manifest
        assert reopened.query(_records()[7].vector, top_k=10) == first

    assert manifest.parameters == parameters
    assert manifest.model_lock_artifact_id == "sha256:model-lock"
    assert first[0].chunk_id == "chunk-0007"


def test_faiss_hnsw_seeded_build_is_input_order_independent(tmp_path: Path) -> None:
    parameters = HnswParameters(m=8, ef_construction=80, ef_search=32, seed=41)
    records = _records(48, 8)
    with FaissHnswIndex.build(
        tmp_path / "forward.sqlite",
        records,
        model_lock_artifact_id="model",
        parameters=parameters,
    ) as forward:
        forward_manifest = forward.manifest
    with FaissHnswIndex.build(
        tmp_path / "reverse.sqlite",
        reversed(records),
        model_lock_artifact_id="model",
        parameters=parameters,
    ) as reverse:
        reverse_manifest = reverse.manifest

    assert reverse_manifest == forward_manifest


def test_faiss_hnsw_measures_recall_against_exact_witness(tmp_path: Path) -> None:
    records = _records()
    queries = [record.vector for record in records[:24]]
    with (
        FaissExactIndex.build(
            tmp_path / "exact.sqlite",
            records,
            model_lock_artifact_id="model",
        ) as exact,
        FaissHnswIndex.build(
            tmp_path / "hnsw.sqlite",
            records,
            model_lock_artifact_id="model",
            parameters=HnswParameters(
                m=16,
                ef_construction=120,
                ef_search=96,
                seed=17,
            ),
        ) as approximate,
    ):
        measurement = measure_hnsw_recall(approximate, exact, queries, k=10)

    assert measurement.query_count == 24
    assert measurement.mean_recall >= 0.99
    assert measurement.minimum_recall >= 0.9
    assert measurement.result_reachability == 1.0
    assert measurement.maximum_score_delta < 1e-5


def test_faiss_hnsw_filters_before_top_k(tmp_path: Path) -> None:
    records = _records()
    with FaissHnswIndex.build(
        tmp_path / "hnsw.sqlite",
        records,
        model_lock_artifact_id="model",
    ) as index:
        results = index.query(records[0].vector, top_k=5, filters={"partition": 1})

    assert len(results) == 5
    assert all(result.metadata["partition"] == 1 for result in results)


def test_faiss_hnsw_detects_graph_and_mapping_corruption(tmp_path: Path) -> None:
    graph_path = tmp_path / "corrupt-graph.sqlite"
    with FaissHnswIndex.build(
        graph_path,
        _records(32, 8),
        model_lock_artifact_id="model",
    ):
        pass
    with sqlite3.connect(graph_path) as connection:
        connection.execute(
            "UPDATE hnsw_index SET serialized_index=? WHERE singleton=1",
            (b"not-faiss",),
        )
    with pytest.raises(FaissHnswIndexCorruptionError, match="checksum"):
        FaissHnswIndex(graph_path)

    mapping_path = tmp_path / "corrupt-mapping.sqlite"
    with FaissHnswIndex.build(
        mapping_path,
        _records(32, 8),
        model_lock_artifact_id="model",
    ):
        pass
    with sqlite3.connect(mapping_path) as connection:
        connection.execute(
            "UPDATE hnsw_records SET chunk_id='tampered' WHERE position=0"
        )
    with pytest.raises(FaissHnswIndexCorruptionError, match="identity"):
        FaissHnswIndex(mapping_path)


def test_faiss_hnsw_failed_replacement_preserves_active_graph(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "hnsw.sqlite"
    with FaissHnswIndex.build(
        path,
        _records(32, 8),
        model_lock_artifact_id="model",
    ) as index:
        generation_id = index.manifest.generation_id

    def reject_publication(
        _source: os.PathLike[str], _target: os.PathLike[str]
    ) -> None:
        raise OSError("injected atomic publication failure")

    monkeypatch.setattr(os, "replace", reject_publication)
    with pytest.raises(OSError, match="publication failure"):
        FaissHnswIndex.build(
            path,
            _records(24, 8),
            model_lock_artifact_id="model",
            replace=True,
        )
    with FaissHnswIndex(path) as reopened:
        assert reopened.manifest.generation_id == generation_id


def test_faiss_hnsw_rejects_invalid_parameters_and_witnesses(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="M"):
        HnswParameters(m=1)
    with pytest.raises(ValueError, match="construction"):
        HnswParameters(m=32, ef_construction=16)
    with pytest.raises(ValueError, match="search"):
        HnswParameters(ef_search=0)
    with pytest.raises(ValueError, match="seed"):
        HnswParameters(seed=-1)

    records = _records(24, 8)
    with (
        FaissExactIndex.build(
            tmp_path / "exact.sqlite",
            records,
            model_lock_artifact_id="exact-model",
        ) as exact,
        FaissHnswIndex.build(
            tmp_path / "hnsw.sqlite",
            records,
            model_lock_artifact_id="other-model",
        ) as approximate,
        pytest.raises(ValueError, match="incompatible"),
    ):
        measure_hnsw_recall(
            approximate,
            exact,
            [records[0].vector],
            k=5,
        )
