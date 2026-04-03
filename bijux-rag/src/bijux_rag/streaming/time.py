# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Time-aware pacing stages (Bijux RAG, sync-only; end-of-Bijux RAG).

These helpers accept injected `clock` and `sleeper` callables to make timing
deterministic and testable. In Bijux RAG they are synchronous and may block
when used with `time.sleep`. Async variants are intentionally deferred.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any, TypeVar

from .types import Transform

T = TypeVar("T")
A = TypeVar("A")


def make_throttle(
    min_delta: float,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> Transform[T, T]:
    """Stage factory: enforce >= min_delta seconds between yielded items."""

    if min_delta < 0:
        raise ValueError("min_delta must be >= 0")

    def stage(items: Iterable[T]) -> Iterator[T]:
        last_emit: float | None = None
        for item in items:
            now = clock()
            if last_emit is not None:
                wait = max(0.0, (last_emit + min_delta) - now)
                if wait > 0:
                    sleeper(wait)
                    now = clock()
            last_emit = now
            yield item

    return stage


def throttle(
    items: Iterable[T],
    *,
    min_delta: float,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> Iterator[T]:
    """Yield items while enforcing a minimum spacing between emissions."""

    stage: Transform[T, T] = make_throttle(min_delta=min_delta, clock=clock, sleeper=sleeper)
    yield from stage(items)


def make_rate_limit(
    rate: float,
    burst: int,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> Transform[T, T]:
    """Token bucket stage: rate tokens/sec, capacity=burst."""

    if rate <= 0:
        raise ValueError("rate must be > 0")
    if burst < 1:
        raise ValueError("burst must be >= 1")

    def stage(items: Iterable[T]) -> Iterator[T]:
        tokens = float(burst)
        last = clock()
        for item in items:
            now = clock()
            tokens = min(float(burst), tokens + (now - last) * rate)
            if tokens < 1.0:
                wait = max(0.0, (1.0 - tokens) / rate)
                if wait > 0:
                    sleeper(wait)
                    now = clock()
                    tokens = min(float(burst), tokens + wait * rate)
            tokens -= 1.0
            last = now
            yield item

    return stage


def make_timestamp(clock: Callable[[], float]) -> Transform[T, tuple[float, T]]:
    """Stage factory: attach a timestamp from the injected clock to each item."""

    def stage(items: Iterable[T]) -> Iterator[tuple[float, T]]:
        for item in items:
            yield (clock(), item)

    return stage


def make_call_gate(
    min_delta: float,
    clock: Callable[[], float],
    sleeper: Callable[[float], None],
) -> Callable[[Callable[..., A], Any], A]:
    """Stateful helper to pace boundary calls (intentionally effectful; use at edges)."""

    if min_delta < 0:
        raise ValueError("min_delta must be >= 0")

    last: float | None = None

    def gate(fn: Callable[..., A], *args: Any, **kwargs: Any) -> A:
        nonlocal last
        now = clock()
        if last is not None:
            wait = max(0.0, (last + min_delta) - now)
            if wait > 0:
                sleeper(wait)
        result = fn(*args, **kwargs)
        last = clock()
        return result

    return gate


__all__ = ["make_throttle", "throttle", "make_rate_limit", "make_timestamp", "make_call_gate"]
