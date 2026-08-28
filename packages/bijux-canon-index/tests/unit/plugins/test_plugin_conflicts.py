# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests for fail-closed plugin registration conflicts."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from bijux_canon_index.infra.adapters.vectorstore_registry import (
    EphemeralVectorStoreAdapter,
    VectorStoreDescriptor,
    VectorStoreRegistry,
)
from bijux_canon_index.infra.embeddings.registry import (
    EmbeddingBatch,
    EmbeddingProvider,
    EmbeddingProviderRegistry,
)
from bijux_canon_index.infra.plugins.contract import PluginContract

CONTRACT = PluginContract(
    determinism="deterministic_exact", randomness_sources=(), approximation=False
)


class _EmbeddingProvider(EmbeddingProvider):
    name = "example"

    def embed(
        self,
        texts: list[str],
        model: str,
        options: Mapping[str, str] | None = None,
    ) -> EmbeddingBatch:
        raise AssertionError("conflict tests must not resolve the provider")


def test_vector_store_name_conflicts_are_rejected() -> None:
    registry = VectorStoreRegistry()
    descriptor = VectorStoreDescriptor(
        name="example",
        available=True,
        supports_exact=True,
        supports_ann=False,
        delete_supported=True,
        filtering_supported=False,
        deterministic_exact=True,
        experimental=True,
    )

    def register() -> None:
        registry.register(
            "example",
            descriptor=descriptor,
            factory=lambda _uri, _options: EphemeralVectorStoreAdapter(),
            contract=CONTRACT,
        )

    register()

    with pytest.raises(ValueError, match="conflicts"):
        register()


def test_embedding_provider_name_conflicts_are_rejected() -> None:
    registry = EmbeddingProviderRegistry()

    def register() -> None:
        registry.register(
            "example", factory=lambda: _EmbeddingProvider(), contract=CONTRACT
        )

    register()

    with pytest.raises(ValueError, match="conflicts"):
        register()
