# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Fan-out helpers for splitting streams (Bijux RAG, end-of-Bijux RAG)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Iterator
from itertools import islice, tee
from typing import TypeVar

from .types import Transform

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


def tap_prefix(items: Iterable[T], k: int, hook: Callable[[tuple[T, ...]], None]) -> Iterator[T]:
    """Bounded side-effect tap: observe up to k items, then yield the full stream."""

    it = iter(items)
    head = tuple(islice(it, k))
    hook(head)
    yield from head
    yield from it


def fork2_lockstep(t: Transform[A, B], u: Transform[A, C]) -> Transform[A, tuple[B, C]]:
    """Strict 1:1 fan-out for transforms.

    Raises ValueError with the mismatch index if one branch produces more items
    than the other.
    """

    def stage(items: Iterable[A]) -> Iterator[tuple[B, C]]:
        a, b = tee(items, 2)
        it1 = iter(t(a))
        it2 = iter(u(b))
        i = 0
        while True:
            try:
                v1 = next(it1)
            except StopIteration:
                try:
                    extra = next(it2)
                except StopIteration:
                    return
                raise ValueError(
                    f"fork2_lockstep mismatch at index={i}: second branch has extra item {extra!r}"
                ) from None

            try:
                v2 = next(it2)
            except StopIteration:
                raise ValueError(
                    f"fork2_lockstep mismatch at index={i}: second branch exhausted early"
                ) from None

            yield (v1, v2)
            i += 1

    return stage


def multicast(items: Iterable[T], n: int, *, maxlen: int = 1024) -> tuple[Iterator[T], ...]:
    """Bounded multicast: return ``n`` independent iterators over the same stream.

    Raises BufferError if consumer skew exceeds maxlen.
    """

    if n <= 0:
        raise ValueError("n must be > 0")
    if maxlen <= 0:
        raise ValueError("maxlen must be > 0")

    upstream = iter(items)
    queues: list[deque[object]] = [deque() for _ in range(n)]
    done = False
    sentinel = object()

    def pump_once() -> None:
        nonlocal done
        if done:
            return
        try:
            x: object = next(upstream)
        except StopIteration:
            done = True
            for q in queues:
                q.append(sentinel)
            return
        for q in queues:
            if len(q) >= maxlen:
                raise BufferError(f"multicast buffer exceeded (maxlen={maxlen})")
            q.append(x)

    def sub(i: int) -> Iterator[T]:
        while True:
            if not queues[i]:
                pump_once()
            item = queues[i].popleft()
            if item is sentinel:
                return
            yield item  # type: ignore[misc]

    return tuple(sub(i) for i in range(n))


__all__ = ["tap_prefix", "fork2_lockstep", "multicast"]
