# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Infrastructure adapters implementing domain ports and capabilities."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS = {
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
    module_name, attr_name = _LAZY_EXPORTS.get(name, (None, None))
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
