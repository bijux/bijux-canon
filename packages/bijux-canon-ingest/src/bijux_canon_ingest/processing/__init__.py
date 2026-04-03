# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Pure document processing primitives for bijux-canon-ingest."""

from __future__ import annotations

from .chunking import (
    gen_chunk_doc,
    gen_chunk_spans,
    gen_overlapping_chunks,
    sliding_windows,
)
from .stages import (
    ChunkAndEmbedConfig,
    ChunkConfig,
    chunk_and_embed_docs,
    chunk_doc,
    clean_doc,
    embed_chunk,
    hash16_embed,
    iter_chunk_doc,
    iter_chunk_spans,
    iter_overlapping_chunks_text,
    structural_dedup_chunks,
)
from .stdlib import chunk_docs, clean_docs, get_doc_id, rag_iter_stdlib
from .streaming import (
    gen_bounded_chunks,
    gen_grouped_chunks,
    gen_stream_deduped,
    gen_stream_embedded,
    safe_rag_pipeline,
    stream_chunks,
)

__all__ = [
    "clean_doc",
    "chunk_doc",
    "iter_chunk_spans",
    "iter_overlapping_chunks_text",
    "iter_chunk_doc",
    "embed_chunk",
    "structural_dedup_chunks",
    "hash16_embed",
    "chunk_and_embed_docs",
    "ChunkAndEmbedConfig",
    "ChunkConfig",
    "gen_chunk_doc",
    "gen_chunk_spans",
    "gen_overlapping_chunks",
    "sliding_windows",
    "gen_grouped_chunks",
    "stream_chunks",
    "gen_stream_embedded",
    "gen_stream_deduped",
    "gen_bounded_chunks",
    "safe_rag_pipeline",
    "clean_docs",
    "chunk_docs",
    "rag_iter_stdlib",
    "get_doc_id",
]
