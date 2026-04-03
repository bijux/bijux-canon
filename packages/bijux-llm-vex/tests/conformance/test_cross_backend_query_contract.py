# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

pytest.importorskip("faiss")

from bijux_vex.core.config import ExecutionConfig, VectorStoreConfig
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    IngestRequest,
)
from bijux_vex.services.execution_engine import VectorExecutionEngine


def _ingest(engine: VectorExecutionEngine) -> None:
    engine.ingest(
        IngestRequest(
            documents=["alpha", "beta", "gamma"],
            vectors=[
                [0.0, 1.0, 0.0],
                [0.0, 0.9, 0.1],
                [0.1, 0.0, 1.0],
            ],
            vector_store=None,
            vector_store_uri=None,
        )
    )
    engine.materialize(
        ExecutionArtifactRequest(
            execution_contract=ExecutionContract.DETERMINISTIC,
            vector_store=None,
            vector_store_uri=None,
        )
    )


def test_cross_backend_query_contract(tmp_path) -> None:
    memory_engine = VectorExecutionEngine(
        config=ExecutionConfig(vector_store=VectorStoreConfig(backend="memory"))
    )
    _ingest(memory_engine)
    memory_result = memory_engine.execute(
        ExecutionRequestPayload(
            vector=(0.0, 1.0, 0.0),
            top_k=3,
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_mode=ExecutionMode.STRICT,
            vector_store="memory",
        )
    )

    index_path = tmp_path / "index.faiss"
    faiss_engine = VectorExecutionEngine(
        config=ExecutionConfig(
            vector_store=VectorStoreConfig(backend="faiss", uri=str(index_path))
        )
    )
    _ingest(faiss_engine)
    faiss_result = faiss_engine.execute(
        ExecutionRequestPayload(
            vector=(0.0, 1.0, 0.0),
            top_k=3,
            execution_contract=ExecutionContract.DETERMINISTIC,
            execution_intent=ExecutionIntent.EXACT_VALIDATION,
            execution_mode=ExecutionMode.STRICT,
            vector_store="faiss",
            vector_store_uri=str(index_path),
        )
    )

    assert memory_result["results"] == faiss_result["results"]
