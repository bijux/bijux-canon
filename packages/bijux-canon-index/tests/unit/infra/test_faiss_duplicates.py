# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

pytest.importorskip("faiss")

from bijux_vex.core.errors import ConflictError
from bijux_vex.infra.adapters.faiss.adapter import FaissVectorStoreAdapter


def test_faiss_rejects_duplicate_vector_ids(tmp_path) -> None:
    adapter = FaissVectorStoreAdapter(uri=str(tmp_path / "index"))
    adapter.connect()
    vectors = [[0.1, 0.2], [0.2, 0.1]]
    metadata = [{"vector_id": "vec-1"}, {"vector_id": "vec-2"}]
    adapter.insert(vectors, metadata=metadata)

    with pytest.raises(ConflictError):
        adapter.insert([[0.3, 0.4]], metadata=[{"vector_id": "vec-1"}])
