# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("faiss")

from bijux_vex.infra.adapters.faiss.adapter import FaissVectorStoreAdapter


def test_faiss_large_ingest_and_query(tmp_path) -> None:
    dimension = 16
    vector_count = 100_000
    query_count = 1_000
    rng = np.random.default_rng(1337)
    vectors = rng.random((vector_count, dimension), dtype=np.float32)
    metadata = [{"vector_id": f"vec-{idx}"} for idx in range(vector_count)]
    adapter = FaissVectorStoreAdapter(uri=str(tmp_path / "index.faiss"))
    adapter.connect()
    adapter.insert(vectors, metadata=metadata)

    for query in vectors[:query_count]:
        results = adapter.query(query.tolist(), k=5, mode="deterministic")
        assert results

    status = adapter.status()
    assert status["index"]["vector_count"] >= vector_count
