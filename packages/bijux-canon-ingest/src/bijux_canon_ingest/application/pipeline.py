# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application-facing ingest pipeline APIs.

This module contains the application entry points for:
- a minimal lazy pipeline (`iter_ingest_pipeline`)
- the fully-configurable instrumented core (`iter_ingest_pipeline_core`)
- the doc-materializing API for taps/observations (`run_ingest_pipeline_docs`)
- a boundary helper that returns a `Result` (`run_ingest_pipeline_path`)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from itertools import chain
from typing import TypeVar

from bijux_canon_ingest.application.pipeline_observations import (
    build_observations,
    tap_items,
)
from bijux_canon_ingest.config.ingest import (
    IngestBoundaryDeps,
    IngestConfig,
    IngestDeps,
)
from bijux_canon_ingest.core.rules_dsl import any_doc
from bijux_canon_ingest.core.rules_pred import eval_pred
from bijux_canon_ingest.core.types import (
    Chunk,
    ChunkWithoutEmbedding,
    CleanDoc,
    DocRule,
    RagEnv,
    RawDoc,
)
from bijux_canon_ingest.fp import StageInstrumentation, instrument_stage
from bijux_canon_ingest.observability import Observations
from bijux_canon_ingest.processing.chunking import gen_chunk_doc
from bijux_canon_ingest.processing.stages import embed_chunk, structural_dedup_chunks
from bijux_canon_ingest.result import Err, Ok, Result

T = TypeVar("T")


def _identity_iter(items: Iterable[RawDoc]) -> Iterable[RawDoc]:
    return items


def iter_ingest_pipeline(
    docs: Iterable[RawDoc],
    env: RagEnv,
    cleaner: Callable[[RawDoc], CleanDoc],
    *,
    keep: DocRule | None = None,
) -> Iterator[Chunk]:
    """Lazy ingest core: filter -> clean -> chunk -> embed without deduplication."""

    rule = keep if keep is not None else any_doc
    kept_docs = (d for d in docs if rule(d))
    cleaned = (cleaner(d) for d in kept_docs)
    chunk_we = (c for cd in cleaned for c in gen_chunk_doc(cd, env))
    embedded = (embed_chunk(c) for c in chunk_we)
    yield from embedded


def iter_ingest_pipeline_core(
    docs: Iterable[RawDoc], config: IngestConfig, deps: IngestDeps
) -> Iterator[Chunk]:
    """Parametric streaming core: filter (RulesConfig) → clean → chunk → embed.

    Stdlib-first note:
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
    chunk_stage: Callable[[Iterable[CleanDoc]], Iterator[ChunkWithoutEmbedding]] = (
        _chunk
    )
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
    config: IngestConfig,
    embedder: Callable[[ChunkWithoutEmbedding], Chunk],
) -> Iterator[Chunk]:
    """Streaming sub-core: chunk + embed from cleaned docs."""

    for cd in cleaned:
        for chunk in gen_chunk_doc(cd, config.env):
            yield embedder(chunk)


def run_ingest_pipeline_docs(
    docs: Iterable[RawDoc],
    config: IngestConfig,
    deps: IngestDeps,
) -> tuple[list[Chunk], Observations]:
    """Document-first API that materializes results for taps and observations."""

    docs_list = list(docs)
    sample_size = config.env.sample_size

    kept_docs = [d for d in docs_list if eval_pred(d, config.keep.keep_pred)]
    tap_items(kept_docs, deps.taps.docs if deps.taps else None)

    cleaned = [deps.cleaner(d) for d in kept_docs]
    tap_items(cleaned, deps.taps.cleaned if deps.taps else None)

    chunks_pre_dedup = list(iter_chunks_from_cleaned(cleaned, config, deps.embedder))
    tap_items(chunks_pre_dedup, deps.taps.chunks if deps.taps else None)

    chunks = structural_dedup_chunks(chunks_pre_dedup)
    obs = build_observations(
        docs=docs_list,
        kept_docs=kept_docs,
        cleaned_docs=cleaned,
        chunks=chunks,
        sample_size=sample_size,
    )
    return chunks, obs


def run_ingest_pipeline(
    docs: Iterable[RawDoc],
    config: IngestConfig,
    deps: IngestDeps,
) -> tuple[list[Chunk], Observations]:
    """Compatibility wrapper for the document-first pipeline API."""

    return run_ingest_pipeline_docs(docs, config, deps)


def run_ingest_pipeline_path(
    path: str,
    config: IngestConfig,
    deps: IngestBoundaryDeps,
) -> Result[tuple[list[Chunk], Observations], str]:
    """Boundary entrypoint that accepts a path and returns a typed result."""

    docs_res = deps.reader.read_docs(path)
    if isinstance(docs_res, Err):
        return Err(docs_res.error)
    chunks, obs = run_ingest_pipeline_docs(docs_res.value, config, deps.core)
    return Ok((chunks, obs))


__all__ = [
    "iter_ingest_pipeline",
    "iter_ingest_pipeline_core",
    "iter_chunks_from_cleaned",
    "run_ingest_pipeline",
    "run_ingest_pipeline_docs",
    "run_ingest_pipeline_path",
]
