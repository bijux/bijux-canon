# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.core.errors import ConflictError
from bijux_canon_index.infra.adapters.faiss.adapter import FaissVectorStoreAdapter


def test_faiss_rejects_duplicate_vector_ids(tmp_path: Path) -> None:
    adapter = FaissVectorStoreAdapter(uri=str(tmp_path / "index"))
    adapter.connect()
    vectors = [[0.1, 0.2], [0.2, 0.1]]
    metadata = [{"vector_id": "vec-1"}, {"vector_id": "vec-2"}]
    adapter.insert(vectors, metadata=metadata)

    with pytest.raises(ConflictError):
        adapter.insert([[0.3, 0.4]], metadata=[{"vector_id": "vec-1"}])
