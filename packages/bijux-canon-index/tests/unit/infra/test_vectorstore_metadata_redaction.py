# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")

from bijux_vex.infra.adapters.qdrant.adapter import QdrantVectorStoreAdapter


def test_qdrant_index_params_do_not_expose_api_key() -> None:
    adapter = QdrantVectorStoreAdapter(
        uri="http://localhost:6333",
        options={"api_key": "secret-key", "batch_size": "8"},
    )
    params = adapter.index_params
    assert "api_key" not in params
