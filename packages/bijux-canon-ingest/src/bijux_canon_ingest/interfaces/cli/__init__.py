# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CLI entrypoints and command helpers."""

from __future__ import annotations

from typing import Any

from bijux_canon_ingest._lazy_exports import LazyExport, resolve_lazy_export

_LAZY_EXPORTS: dict[str, LazyExport] = {
    "FSReader": (".document_io", "FSReader"),
    "boundary_app_config": (".pipeline_runner", "boundary_app_config"),
    "main": (".entrypoint", "main"),
    "orchestrate": (".pipeline_runner", "orchestrate"),
    "read_docs": (".pipeline_runner", "read_docs"),
    "run": (".document_io", "run"),
    "write_chunks": (".pipeline_runner", "write_chunks"),
    "write_chunks_jsonl": (".document_io", "write_chunks_jsonl"),
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
    value = resolve_lazy_export(
        module_name=__name__,
        name=name,
        exports=_LAZY_EXPORTS,
    )
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__) | set(_LAZY_EXPORTS))
