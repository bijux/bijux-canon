# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest

from bijux_canon_index.core.errors import BackendCapabilityError
from bijux_canon_index.infra.adapters.vectorstore import VectorStoreAdapter
from bijux_canon_index.infra.adapters.vectorstore_registry import (
    VECTOR_STORES,
    VectorStoreDescriptor,
    VectorStoreRegistry,
)
from bijux_canon_index.infra.plugins.contract import PluginContract


def test_memory_vector_store_returns_real_exact_results() -> None:
    resolution = VECTOR_STORES.resolve("memory")
    adapter = resolution.adapter

    assert adapter.insert(
        [(1.0, 0.0), (0.0, 1.0)],
        metadata=[{"vector_id": "vector-b"}, {"vector_id": "vector-a"}],
    ) == ["vector-b", "vector-a"]
    assert adapter.query((0.0, 1.0), 2, "deterministic") == [
        ("vector-a", -0.0),
        ("vector-b", -2.0),
    ]
    assert adapter.delete(["vector-a"]) == 1
    assert adapter.query((0.0, 1.0), 2, "deterministic") == [("vector-b", -2.0)]
    assert resolution.descriptor.experimental is True
    assert "excluded from production" in (resolution.descriptor.notes or "")


def test_sqlite_vector_store_alias_fails_closed() -> None:
    resolution = VECTOR_STORES.resolve("sqlite")

    assert resolution.descriptor.supports_exact is False
    assert resolution.descriptor.delete_supported is False
    with pytest.raises(BackendCapabilityError, match="excluded"):
        resolution.adapter.insert(
            [(1.0, 0.0)],
            metadata=[{"vector_id": "vector"}],
        )


class _NoOpPlugin(VectorStoreAdapter):
    is_noop = True

    def connect(self) -> None:
        return

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        del vectors, metadata
        return []

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        del vector, k, mode
        return []

    def delete(self, ids: Iterable[str]) -> int:
        del ids
        return 0


def test_registry_rejects_noop_plugins() -> None:
    registry = VectorStoreRegistry()

    def factory(
        uri: str | None, options: Mapping[str, str] | None
    ) -> VectorStoreAdapter:
        del uri, options
        return _NoOpPlugin()

    registry.register(
        "dishonest",
        descriptor=VectorStoreDescriptor(
            name="dishonest",
            available=True,
            supports_exact=True,
            supports_ann=False,
            delete_supported=True,
            filtering_supported=False,
            deterministic_exact=True,
            experimental=False,
        ),
        factory=factory,
        contract=PluginContract(
            determinism="deterministic_exact",
            randomness_sources=(),
            approximation=False,
        ),
    )

    with pytest.raises(BackendCapabilityError, match="no-op"):
        registry.resolve("dishonest")


def test_qdrant_remains_excluded_without_live_admission() -> None:
    descriptor = next(
        descriptor
        for descriptor in VECTOR_STORES.descriptors()
        if descriptor.name == "qdrant"
    )

    assert descriptor.available is False
    assert descriptor.experimental is True
    assert "no live service admission" in (descriptor.notes or "")
