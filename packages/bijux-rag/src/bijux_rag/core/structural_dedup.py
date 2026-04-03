# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Streaming structural deduplication (Bijux RAG).

Bijux RAG provides a canonical, order-independent deduplication helper
(`structural_dedup_chunks`) that sorts and then removes duplicates.

Bijux RAG introduces a streaming alternative that preserves encounter order:
the first time an item is seen it is yielded, and later duplicates are skipped.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

from bijux_rag.core.rag_types import Chunk

T = TypeVar("T")
K = TypeVar("K", bound=object)


@dataclass
class DedupIterator(Generic[T, K]):
    """Iterator that yields the first occurrence of each key, preserving order."""

    _items: Iterator[T]
    _key: Callable[[T], K]
    _seen: set[K]

    def __init__(self, items: Iterable[T], *, key: Callable[[T], K]) -> None:
        self._items = iter(items)
        self._key = key
        self._seen = set()

    def __iter__(self) -> DedupIterator[T, K]:
        return self

    def __next__(self) -> T:
        while True:
            item = next(self._items)
            k = self._key(item)
            if k not in self._seen:
                self._seen.add(k)
                return item


def structural_dedup_lazy(chunks: Iterable[Chunk]) -> Iterator[Chunk]:
    """Streaming structural dedup for Chunk, preserving encounter order."""

    def key(c: Chunk) -> tuple[str, str, int, int]:
        return (c.doc_id, c.text, c.start, c.end)

    return DedupIterator(chunks, key=key)


__all__ = ["DedupIterator", "structural_dedup_lazy"]
