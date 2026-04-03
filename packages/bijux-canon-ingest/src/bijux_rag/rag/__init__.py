# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""RAG-specific APIs for the end-of-Bijux RAG codebase.

`bijux_rag.fp` contains the module-05 type-driven toolkit. The RAG pipeline
entrypoints live here instead.
"""

from __future__ import annotations

from ..config.cleaning import DEFAULT_CLEAN_CONFIG, CleanConfig, make_cleaner
from ..config.rag import (
    DocsReader,
    RagBoundaryDeps,
    RagConfig,
    RagCoreDeps,
    boundary_rag_config,
    get_deps,
    make_gen_rag_fn,
    make_rag_fn,
)
from ..application.api import (
    full_rag_api,
    full_rag_api_docs,
    full_rag_api_path,
    iter_chunks_from_cleaned,
    iter_rag,
    iter_rag_core,
)
from ..processing import (
    gen_bounded_chunks,
    gen_chunk_doc,
    gen_chunk_spans,
    gen_grouped_chunks,
    gen_overlapping_chunks,
    gen_stream_deduped,
    gen_stream_embedded,
    safe_rag_pipeline,
    sliding_windows,
    stream_chunks,
)
from ..streaming import multicast, throttle
from ..streaming import trace_iter as _trace_iter
from ..application.observability import (
    DebugConfig,
    DocRule,
    Observations,
    RagTaps,
    RagTraceV3,
    TraceLens,
)

__all__ = [
    "DocRule",
    "RagTaps",
    "DebugConfig",
    "Observations",
    "TraceLens",
    "RagTraceV3",
    "CleanConfig",
    "DEFAULT_CLEAN_CONFIG",
    "make_cleaner",
    "RagConfig",
    "RagCoreDeps",
    "DocsReader",
    "RagBoundaryDeps",
    "get_deps",
    "make_rag_fn",
    "make_gen_rag_fn",
    "boundary_rag_config",
    "_trace_iter",
    "gen_chunk_doc",
    "gen_chunk_spans",
    "gen_overlapping_chunks",
    "iter_rag",
    "iter_rag_core",
    "stream_chunks",
    "gen_stream_embedded",
    "gen_stream_deduped",
    "sliding_windows",
    "gen_grouped_chunks",
    "gen_bounded_chunks",
    "safe_rag_pipeline",
    "multicast",
    "throttle",
    "iter_chunks_from_cleaned",
    "full_rag_api",
    "full_rag_api_docs",
    "full_rag_api_path",
]
