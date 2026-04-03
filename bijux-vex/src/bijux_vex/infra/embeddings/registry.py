# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from bijux_vex.core.errors import PluginLoadError
from bijux_vex.infra.plugins.contract import PluginContract
from bijux_vex.infra.plugins.entrypoints import load_entrypoints


@dataclass(frozen=True)
class EmbeddingMetadata:
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
    vectors: list[tuple[float, ...]]
    metadata: EmbeddingMetadata


class EmbeddingProvider(ABC):
    name: str

    @property
    def provider_version(self) -> str | None:
        return None

    @abstractmethod
    def embed(
        self, texts: list[str], model: str, options: Mapping[str, str] | None = None
    ) -> EmbeddingBatch:
        raise NotImplementedError


EmbeddingProviderFactory = Callable[[], EmbeddingProvider]


class EmbeddingProviderRegistry:
    def __init__(self) -> None:
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
        key = (name or self._default or "").lower()
        if not key:
            raise ValueError("Embedding provider name is required")
        if key not in self._providers and key == "example":
            _maybe_register_example(self)
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
        return sorted(self._providers.keys())

    @property
    def default(self) -> str | None:
        return self._default

    def _record_plugin_load(
        self,
        meta: dict[str, str | None],
        *,
        status: str,
        warning: str | None = None,
    ) -> None:
        entry: dict[str, object] = dict(meta)
        entry["status"] = status
        if warning:
            entry["warning"] = warning
        self._plugin_loads.append(entry)

    def _set_active_plugin(self, meta: dict[str, str | None]) -> None:
        self._active_plugin = dict(meta)

    def _clear_active_plugin(self) -> None:
        self._active_plugin = None

    def plugin_reports(self) -> list[dict[str, object]]:
        reports: list[dict[str, object]] = []
        for name, meta in self._plugin_sources.items():
            _factory, contract = self._providers[name]
            reports.append(
                {
                    "name": name,
                    "group": "bijux_vex.embeddings",
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
    try:
        from bijux_vex.infra.embeddings.sentence_transformers import (
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
_register_example_embedding: Callable[[Any], None] | None = None
try:
    from bijux_vex.plugins.example import (
        register_embedding as _register_example_embedding,
    )
except Exception:  # pragma: no cover
    _register_example_embedding = None
if _register_example_embedding is not None:
    _register_example_embedding(EMBEDDING_PROVIDERS)
load_entrypoints("bijux_vex.embeddings", EMBEDDING_PROVIDERS)


def _maybe_register_example(registry: EmbeddingProviderRegistry) -> None:
    try:
        from bijux_vex.plugins.example import register_embedding
    except Exception:
        return
    register_embedding(registry)


__all__ = [
    "EmbeddingMetadata",
    "EmbeddingBatch",
    "EmbeddingProvider",
    "EmbeddingProviderRegistry",
    "EMBEDDING_PROVIDERS",
]
