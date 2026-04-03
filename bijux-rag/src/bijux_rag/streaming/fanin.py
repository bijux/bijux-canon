# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Fan-in helpers for multiple streaming sources (Bijux RAG)."""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterator, Sequence
from typing import Any, TypeVar

from .types import Source

T = TypeVar("T")


def as_source(items: Sequence[T]) -> Source[T]:
    """Turn a re-iterable sequence into a fresh-iterator source."""

    def src() -> Iterator[T]:
        return iter(items)

    return src


def make_chain(*sources: Source[T]) -> Source[T]:
    """Sequential fan-in: yields all items from each source in order."""

    def merged() -> Iterator[T]:
        for src in sources:
            yield from src()

    return merged


def make_roundrobin(*sources: Source[T]) -> Source[T]:
    """Fair-ish interleaving fan-in: cycles sources until all are exhausted."""

    def merged() -> Iterator[T]:
        active = [src() for src in sources]
        while active:
            nxt: list[Iterator[T]] = []
            for it in active:
                try:
                    yield next(it)
                    nxt.append(it)
                except StopIteration:
                    pass
            active = nxt

    return merged


def make_merge(
    *sources: Source[T],
    key: Callable[[T], Any] | None = None,
    reverse: bool = False,
) -> Source[T]:
    """Sorted fan-in: merges already-sorted sources using `heapq.merge`."""

    def merged() -> Iterator[T]:
        iters = [src() for src in sources]
        yield from heapq.merge(*iters, key=key, reverse=reverse)

    return merged


__all__ = ["as_source", "make_chain", "make_roundrobin", "make_merge"]
