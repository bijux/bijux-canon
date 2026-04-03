# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 1: stdlib-first RAG composition examples (end-of-Bijux RAG).

This module exists to demonstrate a pragmatic "stdlib-first" style:
- `functools.partial` for configurators
- `itertools.chain.from_iterable` for flat-mapping
- `operator.attrgetter` for projections

It intentionally reuses the existing pure stage functions from `bijux_rag.rag.stages`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from functools import partial
from itertools import chain
from operator import attrgetter

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, RagEnv, RawDoc
from bijux_rag.rag.stages import clean_doc, embed_chunk, iter_chunk_doc


def clean_docs(docs: Iterable[RawDoc]) -> Iterator[CleanDoc]:
    """Stdlib pipeline: map raw docs to cleaned docs."""

    return map(clean_doc, docs)


def chunk_docs(env: RagEnv) -> Callable[[CleanDoc], Iterator[ChunkWithoutEmbedding]]:
    """Stdlib configurator: return a chunking function specialized to `env`."""

    return partial(iter_chunk_doc, env=env)


def rag_iter_stdlib(docs: Iterable[RawDoc], env: RagEnv) -> Iterator[Chunk]:
    """Stdlib-first end-to-end pipeline: RawDoc -> CleanDoc -> Chunk -> embedding."""

    cleaned = clean_docs(docs)
    chunk_fn = chunk_docs(env)
    chunks: Iterator[ChunkWithoutEmbedding] = chain.from_iterable(map(chunk_fn, cleaned))
    return map(embed_chunk, chunks)


get_doc_id = attrgetter("doc_id")


__all__ = ["clean_docs", "chunk_docs", "rag_iter_stdlib", "get_doc_id"]
