# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Infrastructure adapters implementing domain ports and capabilities."""

from __future__ import annotations

from typing import Any

from bijux_canon_ingest._lazy_exports import LazyExport, resolve_lazy_export

_LAZY_EXPORTS: dict[str, LazyExport] = {
    "AtomicFileStorage": (".atomic_storage", "AtomicFileStorage"),
    "CollectingLogger": (".logger", "CollectingLogger"),
    "ConsoleLogger": (".logger", "ConsoleLogger"),
    "deterministic_embedder_port": (".embedder_port", "deterministic_embedder_port"),
    "FileStorage": (".file_storage", "FileStorage"),
    "InMemoryStorage": (".memory_storage", "InMemoryStorage"),
    "MonotonicTestClock": (".clock", "MonotonicTestClock"),
    "SystemClock": (".clock", "SystemClock"),
}

__all__ = [
    "FileStorage",
    "InMemoryStorage",
    "AtomicFileStorage",
    "SystemClock",
    "MonotonicTestClock",
    "ConsoleLogger",
    "CollectingLogger",
    "deterministic_embedder_port",
]


def __getattr__(name: str) -> Any:
    value = resolve_lazy_export(
        module_name=__name__,
        name=name,
        exports=_LAZY_EXPORTS,
    )
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
