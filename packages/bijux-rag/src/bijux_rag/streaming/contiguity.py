# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Guards for safe `itertools.groupby` usage (Bijux RAG)."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Iterator
from typing import TypeVar

from .types import Transform

T = TypeVar("T")


def ensure_contiguous(key: Callable[[T], Hashable]) -> Transform[T, T]:
    """Stage that enforces contiguity-by-construction for a key (groupby safety)."""

    def stage(items: Iterable[T]) -> Iterator[T]:
        sentinel = object()
        prev: object = sentinel
        seen: set[Hashable] = set()
        for item in items:
            k = key(item)
            if k != prev and k in seen:
                raise ValueError("Non-contiguous key encountered")
            seen.add(k)
            prev = k
            yield item

    return stage


__all__ = ["ensure_contiguous"]
