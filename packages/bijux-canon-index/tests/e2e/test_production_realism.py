# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from bijux_canon_index.application.engine import VectorExecutionEngine
from bijux_canon_index.core.config import ExecutionConfig, VectorStoreConfig
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.infra.embeddings.cache import embedding_config_hash
from bijux_canon_index.infra.embeddings.registry import (
    EMBEDDING_PROVIDERS,
    EmbeddingBatch,
    EmbeddingMetadata,
    EmbeddingProvider,
)
from bijux_canon_index.infra.plugins.contract import PluginContract
from bijux_canon_index.interfaces.schemas.models import (
    ExecutionArtifactRequest,
    ExecutionRequestPayload,
    ExplainRequest,
    IngestRequest,
)
import pytest

pytest.importorskip("faiss")


class StaticTestEmbeddingProvider(EmbeddingProvider):
    name = "static_test"

    def embed(
        self,
        texts: list[str],
        model: str,
        options: Mapping[str, str] | None = None,
    ) -> EmbeddingBatch:
        metadata = EmbeddingMetadata(
            provider=self.name,
            provider_version="tests",
            model=model,
            model_version="tests",
            embedding_determinism="deterministic",
            embedding_seed=0,
            embedding_device="cpu",
            embedding_dtype="float32",
            embedding_normalization="false",
            config_hash=embedding_config_hash(
                self.name,
                model,
                dict(options or {}),
                provider_version="tests",
            ),
        )
        vectors = [tuple(0.0 for _ in range(3)) for _ in texts]
        return EmbeddingBatch(vectors=vectors, metadata=metadata)


def test_production_realism_flow(tmp_path: Path) -> None:
    EMBEDDING_PROVIDERS.register(
        "static_test",
        factory=StaticTestEmbeddingProvider,
        contract=PluginContract(
            determinism="deterministic",
            randomness_sources=(),
            approximation=False,
        ),
    )
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
            embed_provider="static_test",
            embed_model="static_test",
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
    engine.execute(request)
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
