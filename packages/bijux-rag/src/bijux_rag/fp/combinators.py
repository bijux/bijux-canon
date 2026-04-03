# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Small, focused functional helpers for the end-of-Bijux RAG codebase.

This module intentionally stays minimal while supporting:
- Left-to-right function composition
- Lazy iterator combinators (map/filter/flatmap)
- Observation-only taps and probes for debugging
- Deterministic time injection helpers for streaming (Bijux RAG)

Import via `bijux_rag.fp` (package) or `bijux_rag.fp.combinators` (module).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, TypeVar

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
X = TypeVar("X")


def identity(x: A) -> A:
    """Identity function: returns its input unchanged.

    Useful for functor law checks and as a default no-op callback.
    """
    return x


def compose(*functions: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compose unary callables left-to-right into a single unary callable."""

    def composed(value: Any) -> Any:
        out: Any = value
        for fn in functions:
            out = fn(out)
        return out

    return composed


def producer_pipeline(
    producer: Callable[[], Iterable[Any]],
    *stages: Callable[[Iterable[Any]], Iterable[Any]],
) -> Callable[[], Iterable[Any]]:
    """Build a 0-arg pipeline from a producer and iterable→iterable stages."""

    def run() -> Iterable[Any]:
        data: Iterable[Any] = producer()
        for stage in stages:
            data = stage(data)
        return data

    return run


def flow(
    producer: Callable[[], Iterable[Any]],
    *stages: Callable[[Iterable[Any]], Iterable[Any]],
) -> Callable[[], Iterable[Any]]:
    """Alias for ``producer_pipeline`` (kept as the canonical name in the docs)."""

    return producer_pipeline(producer, *stages)


def pipe(value: A, *stages: Callable[[Any], Any]) -> Any:
    """Thread a value through a sequence of unary callables (data-first style)."""
    data: Any = value
    for stage in stages:
        data = stage(data)
    return data


def fmap(func: Callable[[A], B]) -> Callable[[Iterable[A]], Iterator[B]]:
    """Lazy map combinator: lift ``A -> B`` to ``Iterable[A] -> Iterator[B]``."""

    def mapped(items: Iterable[A]) -> Iterator[B]:
        for item in items:
            yield func(item)

    return mapped


def ffilter(pred: Callable[[A], bool]) -> Callable[[Iterable[A]], Iterator[A]]:
    """Lazy filter combinator: lift ``A -> bool`` to ``Iterable[A] -> Iterator[A]``."""

    def filtered(items: Iterable[A]) -> Iterator[A]:
        for item in items:
            if pred(item):
                yield item

    return filtered


def flatmap(func: Callable[[A], Iterable[B]]) -> Callable[[Iterable[A]], Iterator[B]]:
    """Lazy flatmap combinator: lift ``A -> Iterable[B]`` to a flattening stage."""

    def flattened(items: Iterable[A]) -> Iterator[B]:
        for item in items:
            yield from func(item)

    return flattened


def _trace_items(
    items: Iterable[X],
    stage: str,
    *,
    emit: Callable[[str], None],
    formatter: Callable[[X], str],
) -> Iterator[X]:
    for item in items:
        emit(f"{stage}: {formatter(item)}")
        yield item


def _probe_items(items: Iterable[X], stage: str, check_fn: Callable[[X], None]) -> Iterator[X]:
    for item in items:
        try:
            check_fn(item)
        except Exception as exc:  # pragma: no cover - depends on user check_fn
            raise AssertionError(f"probe failed at stage={stage}: {exc}") from exc
        yield item


def tee(
    stage: str,
    *,
    emit: Callable[[str], None] = print,
    formatter: Callable[[Any], str] | None = None,
) -> Callable[[Iterable[Any]], Iterator[Any]]:
    """Observation-only tap that yields values unchanged while emitting logs."""

    fmt: Callable[[Any], str] = formatter if formatter is not None else repr

    def tracer(items: Iterable[Any]) -> Iterator[Any]:
        yield from _trace_items(items, stage, emit=emit, formatter=fmt)

    return tracer


def probe(stage: str, check_fn: Callable[[Any], None]) -> Callable[[Iterable[Any]], Iterator[Any]]:
    """Lazy assertion stage: checks each value, yields unchanged, raises with context."""

    def checker(items: Iterable[Any]) -> Iterator[Any]:
        yield from _probe_items(items, stage, check_fn)

    return checker


@dataclass(frozen=True)
class StageInstrumentation:
    trace: bool = False
    probe_fn: Callable[[Any], None] | None = None
    emit: Callable[[str], None] = print
    formatter: Callable[[Any], str] = repr


def instrument_stage(
    stage: Callable[[Iterable[T_in]], Iterable[T_out]],
    *,
    stage_name: str,
    instrumentation: StageInstrumentation | None = None,
) -> Callable[[Iterable[T_in]], Iterator[T_out]]:
    """Wrap an iterable stage with optional tracing and probing."""

    inst = instrumentation or StageInstrumentation()

    def wrapped(items: Iterable[T_in]) -> Iterator[T_out]:
        out: Iterable[T_out] = stage(items)
        if inst.trace:
            out = _trace_items(out, stage_name, emit=inst.emit, formatter=inst.formatter)
        if inst.probe_fn is not None:
            out = _probe_items(out, stage_name, inst.probe_fn)
        return iter(out)

    return wrapped


class FakeTime:
    """Deterministic, injected time source for testing time-aware streaming stages (Bijux RAG)."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("sleep seconds must be >= 0")
        self.sleeps.append(float(seconds))
        self._now += float(seconds)


__all__ = [
    "identity",
    "compose",
    "producer_pipeline",
    "flow",
    "pipe",
    "fmap",
    "ffilter",
    "flatmap",
    "tee",
    "probe",
    "StageInstrumentation",
    "instrument_stage",
    "FakeTime",
]
