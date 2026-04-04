# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Generator-friendly chunking helpers built on top of the core stages."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator
from typing import TypeVar

from bijux_canon_ingest.core.types import ChunkWithoutEmbedding, CleanDoc, RagEnv
from .stages import (
    iter_chunk_doc,
    iter_chunk_spans,
    iter_overlapping_chunks_text,
)

T = TypeVar("T")


def gen_chunk_doc(doc: CleanDoc, env: RagEnv) -> Iterator[ChunkWithoutEmbedding]:
    """Yield chunk metadata lazily (generator form of ``chunk_doc``)."""

    yield from iter_chunk_doc(doc, env)


def gen_chunk_spans(doc: CleanDoc, env: RagEnv) -> Iterator[tuple[int, int]]:
    """Yield chunk spans lazily (zero-copy alternative to ``gen_chunk_doc``)."""

    yield from iter_chunk_spans(doc, env)


def gen_overlapping_chunks(
    doc_id: str,
    text: str,
    *,
    k: int,
    o: int = 0,
    tail_policy: str = "emit_short",
) -> Iterator[ChunkWithoutEmbedding]:
    """Chunk raw text lazily with overlap and a tail policy."""

    yield from iter_overlapping_chunks_text(
        doc_id, text, k=k, o=o, tail_policy=tail_policy
    )


def sliding_windows(items: Iterable[T], w: int) -> Iterator[tuple[T, ...]]:
    """Yield a sliding window of size ``w`` over ``items`` using bounded auxiliary space."""

    if w <= 0:
        raise ValueError("window size must be > 0")

    it = iter(items)
    buf: deque[T] = deque(maxlen=w)
    for _ in range(w - 1):
        try:
            buf.append(next(it))
        except StopIteration:
            return
    for x in it:
        buf.append(x)
        yield tuple(buf)


__all__ = [
    "gen_chunk_doc",
    "gen_chunk_spans",
    "gen_overlapping_chunks",
    "sliding_windows",
]
