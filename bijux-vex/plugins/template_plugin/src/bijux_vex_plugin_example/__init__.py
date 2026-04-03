# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.infra.adapters.vectorstore_registry import VectorStoreDescriptor
from bijux_vex.infra.plugins.contract import PluginContract


def register(registry) -> None:
    registry.register(
        "template",
        descriptor=VectorStoreDescriptor(
            name="template",
            available=True,
            supports_exact=True,
            supports_ann=False,
            delete_supported=False,
            filtering_supported=False,
            deterministic_exact=True,
            experimental=True,
            consistency="read_after_write",
            notes="template plugin",
        ),
        factory=lambda uri, options: _TemplateAdapter(),
        contract=PluginContract(
            determinism="deterministic_exact",
            randomness_sources=(),
            approximation=False,
        ),
    )


class _TemplateAdapter:
    backend = "template"
    is_noop = False

    def connect(self) -> None:
        return None

    def insert(self, vectors, metadata=None):  # pragma: no cover - template
        return []

    def query(self, vector, k, mode):  # pragma: no cover - template
        return []

    def delete(self, ids):  # pragma: no cover - template
        return 0


__all__ = ["register"]
