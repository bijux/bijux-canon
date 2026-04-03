# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Observation-only helpers for streams (Bijux RAG).

These helpers are intentionally sync and side-effect oriented: they let you
observe streams (logging/metrics/snapshots) without changing the yielded values.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Literal, TypeVar

from .types import Transform

T = TypeVar("T")


def make_tap(
    cb: Callable[[T], None],
    *,
    on_error: Literal["propagate", "suppress"] = "propagate",
) -> Transform[T, T]:
    """Stage factory: call `cb(item)` for side effects and yield items unchanged."""

    def stage(items: Iterable[T]) -> Iterator[T]:
        for item in items:
            try:
                cb(item)
            except Exception:
                if on_error == "propagate":
                    raise
            yield item

    return stage


def make_counter() -> tuple[Callable[[Any], None], Callable[[], dict[str, int]]]:
    """Thread-safe counter callback + metrics snapshot callable."""

    lock = threading.Lock()
    count = 0

    def cb(_: Any) -> None:
        nonlocal count
        with lock:
            count += 1

    def metrics() -> dict[str, int]:
        with lock:
            return {"count": count}

    return cb, metrics


def make_peek(
    n: int,
    emit: Callable[[tuple[T, ...]], None],
    *,
    stride: int = 1,
) -> Transform[T, T]:
    """Emit a bounded window snapshot every `stride` items (does not alter the stream)."""

    if n <= 0:
        raise ValueError("n must be > 0")
    if stride <= 0:
        raise ValueError("stride must be > 0")

    def stage(items: Iterable[T]) -> Iterator[T]:
        buf: deque[T] = deque(maxlen=n)
        for i, item in enumerate(items, start=1):
            buf.append(item)
            if len(buf) == n and (i % stride == 0):
                emit(tuple(buf))
            yield item

    return stage


__all__ = ["make_tap", "make_counter", "make_peek"]
