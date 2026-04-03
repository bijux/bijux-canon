# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

import pytest

from bijux_vex.boundaries.pydantic_edges.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)
from bijux_vex.core.config import ExecutionConfig, VectorStoreConfig
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_vex.plugins.example import register_embedding
from bijux_vex.services.execution_engine import VectorExecutionEngine

pytest.importorskip("faiss")


def test_production_realism_flow(tmp_path: Path) -> None:
    register_embedding(EMBEDDING_PROVIDERS)
    db_path = tmp_path / "state.sqlite"
    index_path = tmp_path / "index.faiss"
    config = ExecutionConfig(
        vector_store=VectorStoreConfig(backend="faiss", uri=str(index_path))
    )
    engine = VectorExecutionEngine(state_path=db_path, config=config)
    engine.ingest(
        IngestRequest(
            documents=["doc-a", "doc-b"],
            vectors=None,
            embed_provider="example",
            embed_model="example",
        )
    )
    engine.materialize(
        ExecutionArtifactRequest(execution_contract=ExecutionContract.DETERMINISTIC)
    )
    request = ExecutionRequestPayload(
        request_text=None,
        vector=(0.0, 0.0, 0.0),
        top_k=1,
        execution_contract=ExecutionContract.DETERMINISTIC,
        execution_intent=ExecutionIntent.EXACT_VALIDATION,
    )
    first = engine.execute(request)
    restarted = VectorExecutionEngine(state_path=db_path, config=config)
    with restarted._tx() as tx:  # pylint: disable=protected-access
        vectors = list(restarted.stores.vectors.list_vectors())
        assert vectors
        restarted.stores.vectors.delete_vector(tx, vectors[0].vector_id)
    adapter = restarted.vector_store_resolution.adapter
    if hasattr(adapter, "rebuild"):
        adapter.rebuild(index_type="exact")
    second = restarted.execute(request)
    assert second["results"]
    explain = restarted.explain(ExplainRequest(result_id=second["results"][0]))
    assert explain["artifact_id"]
