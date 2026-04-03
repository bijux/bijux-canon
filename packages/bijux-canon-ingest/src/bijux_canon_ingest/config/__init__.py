# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Package configuration models and builders."""

from __future__ import annotations

from .app import AppConfig
from .cleaning import DEFAULT_CLEAN_CONFIG, CleanConfig, make_cleaner
from .ingest import (
    DocsReader,
    IngestBoundaryDeps,
    IngestConfig,
    IngestDeps,
    parse_ingest_config,
    build_ingest_deps,
    make_chunk_stream_fn,
    make_ingest_fn,
)

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
