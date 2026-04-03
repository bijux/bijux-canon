# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""RAG pipeline APIs (Bijux RAG–08; end-of-Bijux RAG).

This module contains the domain-specific core pipeline entry points:
- a minimal lazy pipeline (`iter_rag`)
- the fully-configurable instrumented core (`iter_rag_core`)
- the doc-materializing API for taps/observations (`full_rag_api_docs`)
- a boundary helper that returns a `Result` (`full_rag_api_path`)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import chain
from typing import TypeVar

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, DocRule, RagEnv, RawDoc
from bijux_rag.core.rules_dsl import any_doc
from bijux_rag.core.rules_pred import eval_pred
from bijux_rag.fp import StageInstrumentation, instrument_stage
from bijux_rag.rag.stages import embed_chunk, structural_dedup_chunks
from bijux_rag.result import Err, Ok, Result

from .chunking import gen_chunk_doc
from .config import RagBoundaryDeps, RagConfig, RagCoreDeps
from .types import Observations

T = TypeVar("T")


def _identity_iter(items: Iterable[RawDoc]) -> Iterable[RawDoc]:
    return items


def _tap(items: Sequence[T], handler: Callable[[tuple[T, ...]], None] | None) -> Sequence[T]:
    if handler is not None:
        handler(tuple(items))
    return items


def iter_rag(
    docs: Iterable[RawDoc],
    env: RagEnv,
    cleaner: Callable[[RawDoc], CleanDoc],
    *,
    keep: DocRule | None = None,
) -> Iterator[Chunk]:
    """Bijux RAG lazy core: filter → clean → chunk → embed (no dedup)."""

    rule = keep if keep is not None else any_doc
    kept_docs = (d for d in docs if rule(d))
    cleaned = (cleaner(d) for d in kept_docs)
    chunk_we = (c for cd in cleaned for c in gen_chunk_doc(cd, env))
    embedded = (embed_chunk(c) for c in chunk_we)
    yield from embedded


def iter_rag_core(docs: Iterable[RawDoc], config: RagConfig, deps: RagCoreDeps) -> Iterator[Chunk]:
    """Parametric streaming core: filter (RulesConfig) → clean → chunk → embed.

    Bijux RAG stdlib-first note:
    - This pipeline is built from stdlib primitives (`filter`, `map`, `itertools.chain`).
    - Optional tracing/probes are applied via `instrument_stage` only when enabled.
    - See `course-book/reference/fp-standards.md` for the repo's stdlib-first guidance.
    """

    def keep_rule(doc: RawDoc) -> bool:
        return eval_pred(doc, config.keep.keep_pred)

    def check_chunk(chunk: ChunkWithoutEmbedding) -> None:
        if chunk.start < 0 or chunk.end < chunk.start:
            raise ValueError("Invalid chunk offsets")

    def chunker(doc: CleanDoc) -> Iterable[ChunkWithoutEmbedding]:
        return gen_chunk_doc(doc, config.env)

    def _kept(stream: Iterable[RawDoc]) -> Iterator[RawDoc]:
        return filter(keep_rule, stream)

    def _clean(stream: Iterable[RawDoc]) -> Iterator[CleanDoc]:
        return map(deps.cleaner, stream)

    def _chunk(stream: Iterable[CleanDoc]) -> Iterator[ChunkWithoutEmbedding]:
        return chain.from_iterable(map(chunker, stream))

    def _embed(stream: Iterable[ChunkWithoutEmbedding]) -> Iterator[Chunk]:
        return map(deps.embedder, stream)

    kept_stage: Callable[[Iterable[RawDoc]], Iterator[RawDoc]] = _kept
    clean_stage: Callable[[Iterable[RawDoc]], Iterator[CleanDoc]] = _clean
    chunk_stage: Callable[[Iterable[CleanDoc]], Iterator[ChunkWithoutEmbedding]] = _chunk
    embed_stage: Callable[[Iterable[ChunkWithoutEmbedding]], Iterator[Chunk]] = _embed

    if config.debug.trace_kept:
        kept_stage = instrument_stage(
            kept_stage,
            stage_name="kept",
            instrumentation=StageInstrumentation(trace=True),
        )

    if config.debug.trace_clean:
        clean_stage = instrument_stage(
            clean_stage,
            stage_name="clean",
            instrumentation=StageInstrumentation(trace=True),
        )

    if config.debug.trace_chunks or config.debug.probe_chunks:
        chunk_stage = instrument_stage(
            chunk_stage,
            stage_name="chunks",
            instrumentation=StageInstrumentation(
                trace=config.debug.trace_chunks,
                probe_fn=check_chunk if config.debug.probe_chunks else None,
            ),
        )

    if config.debug.trace_embedded:
        embed_stage = instrument_stage(
            embed_stage,
            stage_name="embedded",
            instrumentation=StageInstrumentation(trace=True),
        )

    stream: Iterable[RawDoc] = docs
    if config.debug.trace_docs:
        stream = instrument_stage(
            _identity_iter,
            stage_name="docs",
            instrumentation=StageInstrumentation(trace=True),
        )(stream)
    stream_kept = kept_stage(stream)
    stream_cleaned = clean_stage(stream_kept)
    stream_chunked = chunk_stage(stream_cleaned)
    stream_embedded = embed_stage(stream_chunked)
    yield from stream_embedded


def iter_chunks_from_cleaned(
    cleaned: Iterable[CleanDoc],
    config: RagConfig,
    embedder: Callable[[ChunkWithoutEmbedding], Chunk],
) -> Iterator[Chunk]:
    """Streaming sub-core: chunk + embed from cleaned docs."""

    for cd in cleaned:
        for chunk in gen_chunk_doc(cd, config.env):
            yield embedder(chunk)


def full_rag_api_docs(
    docs: Iterable[RawDoc],
    config: RagConfig,
    deps: RagCoreDeps,
) -> tuple[list[Chunk], Observations]:
    """Doc-based API: materializes at the edge for taps/observations."""

    docs_list = list(docs)
    sample_size = config.env.sample_size

    kept_docs = [d for d in docs_list if eval_pred(d, config.keep.keep_pred)]
    _tap(kept_docs, deps.taps.docs if deps.taps else None)

    cleaned = [deps.cleaner(d) for d in kept_docs]
    _tap(cleaned, deps.taps.cleaned if deps.taps else None)

    chunks_pre_dedup = list(iter_chunks_from_cleaned(cleaned, config, deps.embedder))
    _tap(chunks_pre_dedup, deps.taps.chunks if deps.taps else None)

    chunks = structural_dedup_chunks(chunks_pre_dedup)
    obs = Observations(
        total_docs=len(docs_list),
        kept_docs=len(kept_docs),
        cleaned_docs=len(cleaned),
        total_chunks=len(chunks),
        sample_doc_ids=tuple(d.doc_id for d in kept_docs[:sample_size]),
        sample_chunk_starts=tuple(c.start for c in chunks[:sample_size]),
        extra=(),
        warnings=(),
    )
    return chunks, obs


def full_rag_api(
    docs: Iterable[RawDoc],
    config: RagConfig,
    deps: RagCoreDeps,
) -> tuple[list[Chunk], Observations]:
    """Doc-based API shape used across Modules 02–03 cores."""

    return full_rag_api_docs(docs, config, deps)


def full_rag_api_path(
    path: str,
    config: RagConfig,
    deps: RagBoundaryDeps,
) -> Result[tuple[list[Chunk], Observations], str]:
    """Boundary API shape (introduced in M02C05): path in, Result out."""

    docs_res = deps.reader.read_docs(path)
    if isinstance(docs_res, Err):
        return Err(docs_res.error)
    chunks, obs = full_rag_api_docs(docs_res.value, config, deps.core)
    return Ok((chunks, obs))


__all__ = [
    "iter_rag",
    "iter_rag_core",
    "iter_chunks_from_cleaned",
    "full_rag_api",
    "full_rag_api_docs",
    "full_rag_api_path",
]
