# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>

"""Installable vector-store plugin contract template."""

from __future__ import annotations

from bijux_canon_index.infra.adapters.vectorstore_registry import VectorStoreDescriptor
from bijux_canon_index.infra.plugins.contract import PluginContract


def register(registry) -> None:
    """Register an unavailable template that cannot be mistaken for support."""

    registry.register(
        "template",
        descriptor=VectorStoreDescriptor(
            name="template",
            available=False,
            supports_exact=False,
            supports_ann=False,
            delete_supported=False,
            filtering_supported=False,
            deterministic_exact=False,
            experimental=True,
            consistency=None,
            notes="Implement real persistence and capabilities before enabling.",
        ),
        factory=lambda uri, options: _TemplateAdapter(),
        contract=PluginContract(
            determinism="unimplemented",
            randomness_sources=(),
            approximation=False,
        ),
    )


class _TemplateAdapter:
    backend = "template"
    is_noop = True

    def connect(self) -> None:
        """Keep the template importable without claiming a connection."""

    def insert(self, vectors, metadata=None):  # pragma: no cover - template
        del vectors, metadata
        raise NotImplementedError("template plugin does not implement persistence")

    def query(self, vector, k, mode):  # pragma: no cover - template
        del vector, k, mode
        raise NotImplementedError("template plugin does not implement query")

    def delete(self, ids):  # pragma: no cover - template
        del ids
        raise NotImplementedError("template plugin does not implement deletion")


__all__ = ["register"]
