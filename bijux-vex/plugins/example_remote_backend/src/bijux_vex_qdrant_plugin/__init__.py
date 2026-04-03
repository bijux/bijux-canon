# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.infra.adapters.qdrant.adapter import QdrantVectorStoreAdapter
from bijux_vex.infra.adapters.vectorstore_registry import VectorStoreDescriptor
from bijux_vex.infra.plugins.contract import PluginContract


def register(registry) -> None:
    registry.register(
        "qdrant_plugin_example",
        descriptor=VectorStoreDescriptor(
            name="qdrant_plugin_example",
            available=True,
            supports_exact=True,
            supports_ann=True,
            delete_supported=True,
            filtering_supported=True,
            deterministic_exact=False,
            experimental=True,
            consistency="eventual",
            notes="Example external-style plugin wrapping Qdrant adapter.",
        ),
        factory=lambda uri, options: QdrantVectorStoreAdapter(
            uri=uri, options=options
        ),
        contract=PluginContract(
            determinism="model_dependent",
            randomness_sources=("remote_latency",),
            approximation=True,
        ),
    )


__all__ = ["register"]
