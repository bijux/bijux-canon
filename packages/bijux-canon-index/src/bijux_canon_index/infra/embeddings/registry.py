# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Registry helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from bijux_canon_index.core.errors import PluginLoadError
from bijux_canon_index.infra.plugins.contract import PluginContract
from bijux_canon_index.infra.plugins.entrypoints import load_entrypoints


@dataclass(frozen=True)
class EmbeddingMetadata:
    """Represents embedding metadata."""
    provider: str
    provider_version: str | None
    model: str
    model_version: str | None
    embedding_determinism: str | None
    embedding_seed: int | None
    embedding_device: str | None
    embedding_dtype: str | None
    embedding_normalization: str | None
    config_hash: str


@dataclass(frozen=True)
class EmbeddingBatch:
    """Represents embedding batch."""
    vectors: list[tuple[float, ...]]
    metadata: EmbeddingMetadata


class EmbeddingProvider(ABC):
    """Represents embedding provider."""
    name: str

    @property
    def provider_version(self) -> str | None:
        """Handle provider version."""
        return None

    @abstractmethod
    def embed(
        self, texts: list[str], model: str, options: Mapping[str, str] | None = None
    ) -> EmbeddingBatch:
        """Handle embed."""
        raise NotImplementedError


EmbeddingProviderFactory = Callable[[], EmbeddingProvider]


class EmbeddingProviderRegistry:
    """Represents embedding provider registry."""
    def __init__(self) -> None:
        """Initialize the instance."""
        self._providers: dict[str, tuple[EmbeddingProviderFactory, PluginContract]] = {}
        self._default: str | None = None
        self._plugin_loads: list[dict[str, object]] = []
        self._plugin_sources: dict[str, dict[str, str | None]] = {}
        self._active_plugin: dict[str, str | None] | None = None

    def register(
        self,
        name: str,
        *,
        factory: EmbeddingProviderFactory,
        contract: PluginContract,
        default: bool = False,
    ) -> None:
        """Register name."""
        if not contract.determinism:
            raise ValueError("Embedding provider contract must declare determinism")
        if contract.randomness_sources is None:
            raise ValueError(
                "Embedding provider contract must declare randomness sources"
            )
        key = name.lower()
        self._providers[key] = (factory, contract)
        if default:
            self._default = key
        if self._active_plugin is not None:
            self._plugin_sources[key] = dict(self._active_plugin)

    def resolve(self, name: str | None = None) -> EmbeddingProvider:
        """Resolve name."""
        key = (name or self._default or "").lower()
        if not key:
            raise ValueError("Embedding provider name is required")
        if key not in self._providers:
            raise ValueError(f"Unknown embedding provider: {name}")
        factory, _contract = self._providers[key]
        try:
            return factory()
        except Exception as exc:
            raise PluginLoadError(
                message=f"Embedding plugin failed to initialize: {exc}"
            ) from exc

    def providers(self) -> list[str]:
        """Handle providers."""
        return sorted(self._providers.keys())

    @property
    def default(self) -> str | None:
        """Handle default."""
        return self._default

    def _record_plugin_load(
        self,
        meta: dict[str, str | None],
        *,
        status: str,
        warning: str | None = None,
    ) -> None:
        """Record plugin load."""
        entry: dict[str, object] = dict(meta)
        entry["status"] = status
        if warning:
            entry["warning"] = warning
        self._plugin_loads.append(entry)

    def _set_active_plugin(self, meta: dict[str, str | None]) -> None:
        """Handle set active plugin."""
        self._active_plugin = dict(meta)

    def _clear_active_plugin(self) -> None:
        """Handle clear active plugin."""
        self._active_plugin = None

    def plugin_reports(self) -> list[dict[str, object]]:
        """Handle plugin reports."""
        reports: list[dict[str, object]] = []
        for name, meta in self._plugin_sources.items():
            _factory, contract = self._providers[name]
            reports.append(
                {
                    "name": name,
                    "group": "bijux_canon_index.embeddings",
                    "source": meta.get("name"),
                    "version": meta.get("version"),
                    "entrypoint": meta.get("entrypoint"),
                    "status": "loaded",
                    "determinism": contract.determinism,
                    "randomness_sources": list(contract.randomness_sources),
                    "approximation": contract.approximation,
                }
            )
        reports.extend(
            [entry for entry in self._plugin_loads if entry.get("status") != "loaded"]
        )
        return reports


EMBEDDING_PROVIDERS = EmbeddingProviderRegistry()


def _register_sentence_transformers() -> None:
    """Register sentence transformers."""
    try:
        from bijux_canon_index.infra.embeddings.sentence_transformers import (
            SentenceTransformersProvider,
        )
    except Exception:
        return

    EMBEDDING_PROVIDERS.register(
        "sentence_transformers",
        factory=SentenceTransformersProvider,
        contract=PluginContract(
            determinism="model_dependent",
            randomness_sources=("model_init", "runtime_device"),
            approximation=False,
        ),
        default=True,
    )


_register_sentence_transformers()
load_entrypoints("bijux_canon_index.embeddings", EMBEDDING_PROVIDERS)


__all__ = [
    "EmbeddingMetadata",
    "EmbeddingBatch",
    "EmbeddingProvider",
    "EmbeddingProviderRegistry",
    "EMBEDDING_PROVIDERS",
]
