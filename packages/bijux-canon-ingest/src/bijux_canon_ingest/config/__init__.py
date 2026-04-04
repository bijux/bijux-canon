# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Package configuration models and builders.

The package keeps light-weight cleaning settings available eagerly and resolves
application-facing ingest settings lazily to avoid circular imports during
module initialization.
"""

from __future__ import annotations

from typing import Any

from bijux_canon_ingest._lazy_exports import LazyExport, resolve_lazy_export

from .cleaning import DEFAULT_CLEAN_CONFIG, CleanConfig, make_cleaner

_LAZY_EXPORTS: dict[str, LazyExport] = {
    "AppConfig": (".app", "AppConfig"),
    "DocsReader": (".ingest", "DocsReader"),
    "IngestBoundaryDeps": (".ingest", "IngestBoundaryDeps"),
    "IngestConfig": (".ingest", "IngestConfig"),
    "IngestDeps": (".ingest", "IngestDeps"),
    "parse_ingest_config": (".ingest", "parse_ingest_config"),
    "build_ingest_deps": (".ingest", "build_ingest_deps"),
    "make_chunk_stream_fn": (".ingest", "make_chunk_stream_fn"),
    "make_ingest_fn": (".ingest", "make_ingest_fn"),
}

__all__ = [
    "AppConfig",
    "CleanConfig",
    "DEFAULT_CLEAN_CONFIG",
    "make_cleaner",
    "DocsReader",
    "IngestBoundaryDeps",
    "IngestConfig",
    "IngestDeps",
    "parse_ingest_config",
    "build_ingest_deps",
    "make_chunk_stream_fn",
    "make_ingest_fn",
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
