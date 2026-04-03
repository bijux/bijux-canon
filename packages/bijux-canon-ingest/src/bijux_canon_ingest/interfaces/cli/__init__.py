# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI entrypoints and command helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS = {
    "FSReader": (".file_api", "FSReader"),
    "boundary_app_config": (".pipeline_runner", "boundary_app_config"),
    "main": (".entrypoint", "main"),
    "orchestrate": (".pipeline_runner", "orchestrate"),
    "read_docs": (".pipeline_runner", "read_docs"),
    "run": (".file_api", "run"),
    "write_chunks": (".pipeline_runner", "write_chunks"),
    "write_chunks_jsonl": (".file_api", "write_chunks_jsonl"),
}

__all__ = [
    "FSReader",
    "write_chunks_jsonl",
    "run",
    "main",
    "boundary_app_config",
    "read_docs",
    "write_chunks",
    "orchestrate",
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
