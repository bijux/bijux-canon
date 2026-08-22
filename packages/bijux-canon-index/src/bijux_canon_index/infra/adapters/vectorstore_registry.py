# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Vectorstore registry helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
import math
import threading
from typing import Any, NoReturn
from urllib.parse import urlsplit, urlunsplit

from bijux_canon_index.core.errors import (
    BackendCapabilityError,
    PluginLoadError,
    ValidationError,
)
from bijux_canon_index.infra.adapters.vectorstore import VectorStoreAdapter
from bijux_canon_index.infra.plugins.contract import PluginContract
from bijux_canon_index.infra.plugins.entrypoints import load_entrypoints


@dataclass(frozen=True)
class VectorStoreDescriptor:
    """Represents vector store descriptor."""

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
    """Represents vector store resolution."""

    descriptor: VectorStoreDescriptor
    adapter: VectorStoreAdapter
    uri_redacted: str | None


class EphemeralVectorStoreAdapter(VectorStoreAdapter):
    """Real exact store for development sessions, excluded from production."""

    backend = "memory"

    def __init__(self) -> None:
        self._records: dict[str, tuple[tuple[float, ...], dict[str, Any]]] = {}
        self._dimension: int | None = None
        self._lock = threading.RLock()

    def connect(self) -> None:
        """Handle connect."""
        return

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Handle insert."""
        values = [tuple(float(value) for value in vector) for vector in vectors]
        entries = list(metadata or [])
        if len(values) != len(entries):
            raise ValidationError(message="metadata length must match vectors length")
        if not values:
            return []
        dimension = len(values[0])
        if dimension < 1 or any(
            len(vector) != dimension
            or any(not math.isfinite(value) for value in vector)
            for vector in values
        ):
            raise ValidationError(message="memory vectors must be finite and uniform")
        vector_ids = []
        with self._lock:
            if self._dimension is not None and self._dimension != dimension:
                raise ValidationError(message="memory vector dimension mismatch")
            self._dimension = dimension
            for vector, entry in zip(values, entries, strict=True):
                vector_id = entry.get("vector_id")
                if not vector_id:
                    raise ValidationError(message="vector_id is required")
                identity = str(vector_id)
                if identity in self._records:
                    raise ValidationError(message="vector_id already exists")
                self._records[identity] = (vector, dict(entry))
                vector_ids.append(identity)
        return vector_ids

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        """Query vector."""
        del mode
        values = tuple(float(value) for value in vector)
        if k < 1:
            raise ValidationError(message="query result count must be positive")
        with self._lock:
            if self._dimension is None:
                return []
            if len(values) != self._dimension or any(
                not math.isfinite(value) for value in values
            ):
                raise ValidationError(message="memory query dimension mismatch")
            scored = [
                (
                    vector_id,
                    -sum(
                        (query_value - stored_value) ** 2
                        for query_value, stored_value in zip(
                            values, stored_vector, strict=True
                        )
                    ),
                )
                for vector_id, (stored_vector, _metadata) in self._records.items()
            ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:k]

    def delete(self, ids: Iterable[str]) -> int:
        """Handle delete."""
        identities = {str(identity) for identity in ids}
        with self._lock:
            removed = sum(identity in self._records for identity in identities)
            for identity in identities:
                self._records.pop(identity, None)
            if not self._records:
                self._dimension = None
        return removed


class ExcludedVectorStoreAdapter(VectorStoreAdapter):
    """Fail-closed adapter for a named surface excluded from production."""

    def __init__(self, backend: str, reason: str) -> None:
        self.backend = backend
        self._reason = reason

    def connect(self) -> None:
        """Validate the explicit exclusion without claiming connectivity."""

    def _raise(self) -> NoReturn:
        raise BackendCapabilityError(
            message=(
                f"vector store '{self.backend}' is excluded: {self._reason}; "
                "use the persistent SQLite FTS5 or FAISS generation APIs"
            )
        )

    def insert(
        self,
        vectors: Iterable[Sequence[float]],
        metadata: Iterable[dict[str, Any]] | None = None,
    ) -> list[str]:
        del vectors, metadata
        self._raise()

    def query(
        self, vector: Sequence[float], k: int, mode: str
    ) -> list[tuple[str, float]]:
        del vector, k, mode
        self._raise()

    def delete(self, ids: Iterable[str]) -> int:
        del ids
        self._raise()


VectorStoreFactory = Callable[
    [str | None, Mapping[str, str] | None], VectorStoreAdapter
]
AvailabilityCheck = Callable[[], tuple[bool, str | None, str | None]]


def _redact_uri(uri: str | None) -> str | None:
    """Handle redact uri."""
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
    """Represents vector store registry."""

    def __init__(self) -> None:
        """Initialize the instance."""
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
        """Register name."""
        key = name.lower()
        if not contract.determinism:
            raise ValueError("Plugin contract must declare determinism")
        if contract.randomness_sources is None:
            raise ValueError("Plugin contract must declare randomness sources")
        if key in self._entries:
            raise ValueError(f"Vector store plugin name conflicts with {key!r}")
        self._entries[key] = (descriptor, factory, availability, contract)
        if self._active_plugin is not None:
            self._plugin_sources[key] = dict(self._active_plugin)

    def resolve(
        self,
        name: str,
        uri: str | None = None,
        options: Mapping[str, str] | None = None,
    ) -> VectorStoreResolution:
        """Resolve name."""
        if not name:
            raise ValidationError(message="vector store name is required")
        raw = name.lower()
        key = raw[4:] if raw.startswith("vdb:") else raw
        if key not in self._entries:
            raise ValidationError(
                message=(
                    "What happened: unknown vector store backend.\n"
                    f"Why: '{name}' is not registered.\n"
                    "How to fix: choose a backend listed in `bijux capabilities` or install the plugin.\n"
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
        if getattr(adapter, "is_noop", False):
            raise BackendCapabilityError(
                message=(
                    "What happened: vector store backend was rejected.\n"
                    f"Why: '{descriptor.name}' resolved to no-op behavior.\n"
                    "How to fix: install or select a backend that persists real results."
                )
            )
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
        """Handle descriptors."""
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
            descriptor, _factory, _availability, contract = self._entries[name]
            reports.append(
                {
                    "name": name,
                    "group": "bijux_canon_index.vectorstores",
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


def _memory_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    del uri, options
    return EphemeralVectorStoreAdapter()


def _excluded_sqlite_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    del uri, options
    return ExcludedVectorStoreAdapter(
        "sqlite",
        "the former alias discarded vector writes and was not a persistent index",
    )


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
        experimental=True,
        consistency="read_after_write",
        notes="real ephemeral exact store; excluded from production profiles",
    ),
    factory=_memory_factory,
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
        supports_exact=False,
        supports_ann=False,
        delete_supported=False,
        filtering_supported=False,
        deterministic_exact=False,
        experimental=True,
        consistency=None,
        notes="excluded alias; use the persistent SQLite FTS5 generation API",
    ),
    factory=_excluded_sqlite_factory,
    contract=PluginContract(
        determinism="deterministic_exact",
        randomness_sources=(),
        approximation=False,
    ),
)


def _faiss_available() -> tuple[bool, str | None, str | None]:
    """Handle FAISS available."""
    try:
        import faiss  # type: ignore[import-untyped]

        return True, getattr(faiss, "__version__", None), None
    except Exception:
        return False, None, "faiss-cpu not installed"


def _faiss_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    """Handle FAISS factory."""
    from bijux_canon_index.infra.adapters.faiss.adapter import FaissVectorStoreAdapter

    return FaissVectorStoreAdapter(uri=uri, options=options)


def _qdrant_available() -> tuple[bool, str | None, str | None]:
    """Exclude Qdrant until a live service is explicitly admitted."""
    try:
        import qdrant_client

        return (
            False,
            getattr(qdrant_client, "__version__", None),
            "experimental excluded: no live service admission is recorded",
        )
    except Exception:
        return (
            False,
            None,
            "experimental excluded: no live service admission is recorded; "
            "qdrant-client is not installed",
        )


def _qdrant_factory(
    uri: str | None, options: Mapping[str, str] | None
) -> VectorStoreAdapter:
    """Handle Qdrant factory."""
    from bijux_canon_index.infra.adapters.qdrant.adapter import QdrantVectorStoreAdapter

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

load_entrypoints("bijux_canon_index.vectorstores", VECTOR_STORES)


__all__ = [
    "VectorStoreDescriptor",
    "VectorStoreResolution",
    "VectorStoreRegistry",
    "VECTOR_STORES",
    "EphemeralVectorStoreAdapter",
    "ExcludedVectorStoreAdapter",
]
