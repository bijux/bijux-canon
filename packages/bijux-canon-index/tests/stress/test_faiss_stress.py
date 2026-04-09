# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("faiss")


def test_faiss_large_ingest_and_query(tmp_path: Path) -> None:
    from bijux_canon_index.infra.adapters.faiss.adapter import FaissVectorStoreAdapter

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

    status = cast(dict[str, Any], adapter.status())
    index_status = cast(dict[str, int], status["index"])
    assert index_status["vector_count"] >= vector_count
