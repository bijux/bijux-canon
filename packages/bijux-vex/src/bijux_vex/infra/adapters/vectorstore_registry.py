# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from bijux_vex.core.errors import (
    BackendCapabilityError,
    PluginLoadError,
    ValidationError,
)
from bijux_vex.infra.adapters.vectorstore import VectorStoreAdapter
from bijux_vex.infra.plugins.contract import PluginContract
from bijux_vex.infra.plugins.entrypoints import load_entrypoints


@dataclass(frozen=True)
class VectorStoreDescriptor:
    name: str
    available: bool
    supports_exact: bool
    supports_ann: bool
    delete_supported: bool
    filtering_supported: bool
    deterministic_exact: bool
    experimental: bool
    consistency: str | None = None
    notes: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class VectorStoreResolution:
    descriptor: VectorStoreDescriptor
    adapter: VectorStoreAdapter
    uri_redacted: str | None


class NoOpVectorStoreAdapter(VectorStoreAdapter):
    backend = "memory"
    is_noop = True

    def connect(self) -> None:
        return None

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        if metadata:
            return [entry.get("vector_id", "") for entry in metadata]
        return []

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        return []

    def delete(self, ids: Iterable[str]) -> int:
        return 0


VectorStoreFactory = Callable[
    [str | None, Mapping[str, str] | None], VectorStoreAdapter
]
AvailabilityCheck = Callable[[], tuple[bool, str | None, str | None]]


def _redact_uri(uri: str | None) -> str | None:
    if uri is None:
        return None
    parts = urlsplit(uri)
    if not parts.scheme or not parts.netloc:
        return uri
    userinfo, _, host = parts.netloc.rpartition("@")
    if not userinfo:
        return uri
    username, _, _password = userinfo.partition(":")
    redacted_userinfo = f"{username}:***" if username else "***"
    return urlunsplit(
        (
            parts.scheme,
            f"{redacted_userinfo}@{host}",
            parts.path,
            parts.query,
            parts.fragment,
        )
    )


class VectorStoreRegistry:
    def __init__(self) -> None:
        self._entries: dict[
            str,
            tuple[
                VectorStoreDescriptor,
                VectorStoreFactory,
                AvailabilityCheck | None,
                PluginContract,
            ],
        ] = {}
        self._plugin_loads: list[dict[str, object]] = []
        self._plugin_sources: dict[str, dict[str, str | None]] = {}
        self._active_plugin: dict[str, str | None] | None = None

    def register(
        self,
        name: str,
        *,
        descriptor: VectorStoreDescriptor,
        factory: VectorStoreFactory,
        contract: PluginContract,
        availability: AvailabilityCheck | None = None,
    ) -> None:
        key = name.lower()
        if not contract.determinism:
            raise ValueError("Plugin contract must declare determinism")
        if contract.randomness_sources is None:
            raise ValueError("Plugin contract must declare randomness sources")
        self._entries[key] = (descriptor, factory, availability, contract)
        if self._active_plugin is not None:
            self._plugin_sources[key] = dict(self._active_plugin)

    def resolve(
        self,
        name: str,
        uri: str | None = None,
        options: Mapping[str, str] | None = None,
    ) -> VectorStoreResolution:
        if not name:
            raise ValidationError(message="vector store name is required")
        raw = name.lower()
        key = raw[4:] if raw.startswith("vdb:") else raw
        if key not in self._entries:
            raise ValidationError(
                message=(
                    "What happened: unknown vector store backend.\n"
                    f"Why: '{name}' is not registered.\n"
                    "How to fix: choose a backend listed in `bijux vex capabilities` or install the plugin.\n"
                    "Where to learn more: docs/spec/vectorstore_adapter.md"
                )
            )
        descriptor, factory, availability, _contract = self._entries[key]
        available = descriptor.available
        version = descriptor.version
        notes = descriptor.notes
        if availability is not None:
            available, version, notes = availability()
        if not available:
            hint = f" (install extras for {descriptor.name})" if descriptor.name else ""
            raise BackendCapabilityError(
                message=(
                    "What happened: vector store backend unavailable.\n"
                    f"Why: '{descriptor.name}' could not be loaded{hint}.\n"
                    "How to fix: install the matching extras and retry.\n"
                    "Where to learn more: docs/spec/vectorstore_adapter.md"
                )
            )
        resolved_descriptor = VectorStoreDescriptor(
            name=descriptor.name,
            available=True,
            supports_exact=descriptor.supports_exact,
            supports_ann=descriptor.supports_ann,
            delete_supported=descriptor.delete_supported,
            filtering_supported=descriptor.filtering_supported,
            deterministic_exact=descriptor.deterministic_exact,
            experimental=descriptor.experimental,
            consistency=descriptor.consistency,
            notes=notes,
            version=version,
        )
        try:
            adapter = factory(uri, options)
        except Exception as exc:
            raise PluginLoadError(
                message=f"Vector store plugin failed to initialize: {exc}"
            ) from exc
        try:
            adapter.connect()
        except Exception as exc:
            raise BackendCapabilityError(
                message=(
                    "What happened: failed to connect to vector store.\n"
                    f"Why: backend '{descriptor.name}' raised {exc}.\n"
                    "How to fix: verify the URI/options and backend installation.\n"
                    "Where to learn more: docs/spec/failure_semantics.md"
                )
            ) from exc
        return VectorStoreResolution(
            descriptor=resolved_descriptor,
            adapter=adapter,
            uri_redacted=_redact_uri(uri),
        )

    def descriptors(self) -> list[VectorStoreDescriptor]:
        items: list[VectorStoreDescriptor] = []
        for _, (descriptor, _factory, availability, _contract) in sorted(
            self._entries.items()
        ):
            available = descriptor.available
            version = descriptor.version
            notes = descriptor.notes
            if availability is not None:
                available, version, notes = availability()
            items.append(
                VectorStoreDescriptor(
                    name=descriptor.name,
                    available=available,
                    supports_exact=descriptor.supports_exact,
                    supports_ann=descriptor.supports_ann,
                    delete_supported=descriptor.delete_supported,
                    filtering_supported=descriptor.filtering_supported,
                    deterministic_exact=descriptor.deterministic_exact,
                    experimental=descriptor.experimental,
                    consistency=descriptor.consistency,
                    notes=notes,
                    version=version,
                )
            )
        return items

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
            descriptor, _factory, _availability, contract = self._entries[name]
            reports.append(
                {
                    "name": name,
                    "group": "bijux_vex.vectorstores",
                    "source": meta.get("name"),
                    "version": meta.get("version"),
                    "entrypoint": meta.get("entrypoint"),
                    "status": "loaded",
                    "determinism": contract.determinism,
                    "randomness_sources": list(contract.randomness_sources),
                    "approximation": contract.approximation,
                    "capabilities": {
                        "supports_exact": descriptor.supports_exact,
                        "supports_ann": descriptor.supports_ann,
                        "delete_supported": descriptor.delete_supported,
                        "filtering_supported": descriptor.filtering_supported,
                    },
                }
            )
        reports.extend(
            [entry for entry in self._plugin_loads if entry.get("status") != "loaded"]
        )
        return reports


VECTOR_STORES = VectorStoreRegistry()


def _noop_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    return NoOpVectorStoreAdapter()


VECTOR_STORES.register(
    "memory",
    descriptor=VectorStoreDescriptor(
        name="memory",
        available=True,
        supports_exact=True,
        supports_ann=False,
        delete_supported=True,
        filtering_supported=False,
        deterministic_exact=True,
        experimental=False,
        consistency="read_after_write",
        notes="no-op adapter; uses local vector source",
    ),
    factory=_noop_factory,
    contract=PluginContract(
        determinism="deterministic_exact",
        randomness_sources=(),
        approximation=False,
    ),
)
VECTOR_STORES.register(
    "sqlite",
    descriptor=VectorStoreDescriptor(
        name="sqlite",
        available=True,
        supports_exact=True,
        supports_ann=False,
        delete_supported=True,
        filtering_supported=False,
        deterministic_exact=True,
        experimental=False,
        consistency="read_after_write",
        notes="alias for local storage (no-op adapter)",
    ),
    factory=_noop_factory,
    contract=PluginContract(
        determinism="deterministic_exact",
        randomness_sources=(),
        approximation=False,
    ),
)


def _faiss_available() -> tuple[bool, str | None, str | None]:
    try:
        import faiss

        return True, getattr(faiss, "__version__", None), None
    except Exception:
        return False, None, "faiss-cpu not installed"


def _faiss_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    from bijux_vex.infra.adapters.faiss.adapter import FaissVectorStoreAdapter

    return FaissVectorStoreAdapter(uri=uri, options=options)


def _qdrant_available() -> tuple[bool, str | None, str | None]:
    try:
        import qdrant_client

        return True, getattr(qdrant_client, "__version__", None), None
    except Exception:
        return False, None, "qdrant-client not installed"


def _qdrant_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    from bijux_vex.infra.adapters.qdrant.adapter import QdrantVectorStoreAdapter

    return QdrantVectorStoreAdapter(uri=uri, options=options)


VECTOR_STORES.register(
    "faiss",
    descriptor=VectorStoreDescriptor(
        name="faiss",
        available=False,
        supports_exact=True,
        supports_ann=True,
        delete_supported=True,
        filtering_supported=False,
        deterministic_exact=True,
        experimental=True,
        consistency="read_after_write",
        notes="local FAISS index (exact or ANN depending on index_type)",
    ),
    factory=_faiss_factory,
    contract=PluginContract(
        determinism="deterministic_exact",
        randomness_sources=(),
        approximation=False,
    ),
    availability=_faiss_available,
)
VECTOR_STORES.register(
    "qdrant",
    descriptor=VectorStoreDescriptor(
        name="qdrant",
        available=False,
        supports_exact=True,
        supports_ann=True,
        delete_supported=True,
        filtering_supported=True,
        deterministic_exact=False,
        experimental=True,
        consistency="eventual",
        notes="remote Qdrant vector store",
    ),
    factory=_qdrant_factory,
    contract=PluginContract(
        determinism="model_dependent",
        randomness_sources=("index_state",),
        approximation=True,
    ),
    availability=_qdrant_available,
)

load_entrypoints("bijux_vex.vectorstores", VECTOR_STORES)


__all__ = [
    "VectorStoreDescriptor",
    "VectorStoreResolution",
    "VectorStoreRegistry",
    "VECTOR_STORES",
    "NoOpVectorStoreAdapter",
]
