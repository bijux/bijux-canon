# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("qdrant_client")

from bijux_canon_index.infra.adapters.qdrant.adapter import QdrantVectorStoreAdapter


class _StubClient:
    def __init__(self) -> None:
        self.upsert_calls = 0
        self.ids: set[str] = set()

    def collection_exists(self, name: str) -> bool:
        return True

    def create_collection(self, **kwargs: Any) -> None:  # pragma: no cover - unused
        return None

    def upsert(self, collection_name: str, points: list[Any]) -> None:
        self.upsert_calls += 1
        if self.upsert_calls == 1:
            raise TimeoutError("timeout")
        for point in points:
            self.ids.add(str(point.id))


def test_qdrant_upsert_retries_are_idempotent() -> None:
    adapter = QdrantVectorStoreAdapter(
        uri="http://localhost:6333",
        options={"retry_count": "1", "batch_size": "2"},
    )
    adapter._client = _StubClient()

    vectors = [[0.1, 0.2], [0.2, 0.1], [0.3, 0.4]]
    metadata = [
        {"vector_id": "vec-1"},
        {"vector_id": "vec-2"},
        {"vector_id": "vec-3"},
    ]
    adapter.insert(vectors, metadata=metadata)
    assert adapter._client.upsert_calls == 2
    assert len(adapter._client.ids) == 3
