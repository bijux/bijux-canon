# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from bijux_vex.infra.adapters.vectorstore import VectorStoreAdapter
from bijux_vex.infra.adapters.vectorstore_registry import VectorStoreDescriptor
from bijux_vex.infra.embeddings.cache import embedding_config_hash
from bijux_vex.infra.embeddings.registry import (
    EmbeddingBatch,
    EmbeddingMetadata,
    EmbeddingProvider,
)
from bijux_vex.infra.plugins.contract import PluginContract


class ExampleVectorStore(VectorStoreAdapter):
    backend = "example"

    def connect(self) -> None:
        return None

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        return [entry.get("vector_id", "") for entry in (metadata or [])]

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        return []

    def delete(self, ids: Iterable[str]) -> int:
        return 0


class ExampleEmbeddingProvider(EmbeddingProvider):
    name = "example"

    def embed(
        self, texts: list[str], model: str, options: Mapping[str, str] | None = None
    ) -> EmbeddingBatch:
        vectors = [tuple(0.0 for _ in range(3)) for _ in texts]
        metadata = EmbeddingMetadata(
            provider=self.name,
            provider_version="example-1",
            model=model,
            model_version="example",
            embedding_determinism="deterministic",
            embedding_seed=0,
            embedding_device="cpu",
            embedding_dtype="float32",
            embedding_normalization="false",
            config_hash=embedding_config_hash(
                self.name, model, options or {}, provider_version="example-1"
            ),
        )
        return EmbeddingBatch(vectors=vectors, metadata=metadata)


class ExampleRunner:
    pass


def register_vectorstore(registry: Any) -> None:
    registry.register(
        "example",
        descriptor=VectorStoreDescriptor(
            name="example",
            available=True,
            supports_exact=True,
            supports_ann=False,
            delete_supported=True,
            filtering_supported=False,
            deterministic_exact=True,
            experimental=True,
            consistency="read_after_write",
            notes="example plugin adapter",
        ),
        factory=lambda uri, options: ExampleVectorStore(),
        contract=PluginContract(
            determinism="deterministic_exact",
            randomness_sources=(),
            approximation=False,
        ),
    )


def register_embedding(registry: Any) -> None:
    registry.register(
        "example",
        factory=ExampleEmbeddingProvider,
        contract=PluginContract(
            determinism="deterministic",
            randomness_sources=(),
            approximation=False,
        ),
        default=False,
    )


def register_runner(registry: Any) -> None:
    registry.register(
        "example",
        factory=ExampleRunner,
        contract=PluginContract(
            determinism="deterministic",
            randomness_sources=(),
            approximation=False,
        ),
    )


__all__ = [
    "register_vectorstore",
    "register_embedding",
    "register_runner",
]
