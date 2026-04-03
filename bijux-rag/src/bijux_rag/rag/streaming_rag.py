# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Streaming RAG helpers (Bijux RAG+; end-of-Bijux RAG).

These functions keep the core pipeline lazy while optionally fencing work,
grouping by doc, and tracing samples.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from itertools import dropwhile, groupby, islice
from operator import attrgetter
from typing import TypeVar

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, RawDoc
from bijux_rag.core.rules_pred import eval_pred
from bijux_rag.core.structural_dedup import structural_dedup_lazy
from bijux_rag.streaming import TraceLens, ensure_contiguous, trace_iter

from .chunking import gen_chunk_doc
from .config import RagConfig, RagCoreDeps

T = TypeVar("T")


def gen_grouped_chunks(
    chunks: Iterable[ChunkWithoutEmbedding],
) -> Iterator[tuple[str, Iterator[ChunkWithoutEmbedding]]]:
    """Group contiguous chunk runs by ``doc_id`` (Bijux RAG)."""

    guarded = ensure_contiguous(attrgetter("doc_id"))(chunks)
    yield from groupby(guarded, key=attrgetter("doc_id"))


def stream_chunks(
    docs: Iterable[RawDoc],
    config: RagConfig,
    deps: RagCoreDeps,
    *,
    trace_docs: TraceLens[RawDoc] | None = None,
    trace_cleaned: TraceLens[CleanDoc] | None = None,
    trace_chunks: TraceLens[ChunkWithoutEmbedding] | None = None,
) -> Iterator[ChunkWithoutEmbedding]:
    """Streaming chunks core: filter → clean → chunk (no embedding, no dedup)."""

    stream: Iterable[RawDoc] = docs
    if trace_docs is not None:
        stream = trace_iter(stream, trace_docs)

    kept = (d for d in stream if eval_pred(d, config.keep.keep_pred))
    cleaned: Iterable[CleanDoc] = (deps.cleaner(d) for d in kept)
    if trace_cleaned is not None:
        cleaned = trace_iter(cleaned, trace_cleaned)

    chunked: Iterable[ChunkWithoutEmbedding] = (
        c for cd in cleaned for c in gen_chunk_doc(cd, config.env)
    )
    if trace_chunks is not None:
        chunked = trace_iter(chunked, trace_chunks)
    yield from chunked


def gen_stream_embedded(
    chunks: Iterable[ChunkWithoutEmbedding],
    embedder: Callable[[ChunkWithoutEmbedding], Chunk],
    *,
    trace_embedded: TraceLens[Chunk] | None = None,
) -> Iterator[Chunk]:
    """Streaming embedding stage: chunk_without_embedding → chunk."""

    embedded: Iterable[Chunk] = (embedder(c) for c in chunks)
    if trace_embedded is not None:
        embedded = trace_iter(embedded, trace_embedded)
    yield from embedded


def gen_stream_deduped(chunks: Iterable[Chunk]) -> Iterator[Chunk]:
    """Streaming structural dedup stage (order-preserving)."""

    yield from structural_dedup_lazy(chunks)


def gen_bounded_chunks(
    docs: Iterable[RawDoc],
    config: RagConfig,
    deps: RagCoreDeps,
    *,
    max_chunks: int | None = None,
) -> Iterator[ChunkWithoutEmbedding]:
    """Hard fence on the number of chunks produced (Bijux RAG)."""

    chunked = stream_chunks(docs, config, deps)
    if max_chunks is None:
        yield from chunked
        return
    yield from islice(chunked, max_chunks)


def safe_rag_pipeline(
    docs: Iterable[RawDoc],
    config: RagConfig,
    deps: RagCoreDeps,
    *,
    max_chunks: int = 10_000,
    min_doc_len: int = 500,
) -> Iterator[ChunkWithoutEmbedding]:
    """Defensive streaming pipeline with explicit fences (Bijux RAG)."""

    fenced_docs = dropwhile(lambda d: len(d.abstract) < min_doc_len, docs)
    yield from gen_bounded_chunks(fenced_docs, config, deps, max_chunks=max_chunks)


__all__ = [
    "gen_grouped_chunks",
    "stream_chunks",
    "gen_stream_embedded",
    "gen_stream_deduped",
    "gen_bounded_chunks",
    "safe_rag_pipeline",
]
