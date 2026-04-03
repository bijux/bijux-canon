# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG monoids and semigroups: associative aggregation with identities (end-of-Bijux RAG)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Generic, Iterable, List, Tuple, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")


@dataclass(frozen=True, slots=True)
class Monoid(Generic[T]):
    empty: Callable[[], T]
    combine: Callable[[T, T], T]


@dataclass(frozen=True, slots=True)
class Semi(Generic[T]):
    combine: Callable[[T, T], T]


def fold(m: Monoid[T], xs: Iterable[T]) -> T:
    acc = m.empty()
    for x in xs:
        acc = m.combine(acc, x)
    return acc


def fold_map(m: Monoid[T], f: Callable[[U], T], xs: Iterable[U]) -> T:
    return fold(m, map(f, xs))


def tree_reduce(m: Monoid[T], xs: Iterable[T], chunk: int = 2048) -> T:
    buf: List[T] = []
    for x in xs:
        buf.append(x)
        if len(buf) >= chunk:
            buf = [_tree_combine(m, buf)]
    return _tree_combine(m, buf) if buf else m.empty()


def _tree_combine(m: Monoid[T], items: List[T]) -> T:
    while len(items) > 1:
        next_items: List[T] = []
        it = iter(items)
        for a in it:
            b = next(it, None)
            next_items.append(a if b is None else m.combine(a, b))
        items = next_items
    return items[0] if items else m.empty()


@dataclass(frozen=True, slots=True)
class Sum:
    value: int


SUM_INT: Monoid[Sum] = Monoid(empty=lambda: Sum(0), combine=lambda a, b: Sum(a.value + b.value))


LIST_STR: Monoid[List[str]] = Monoid(empty=list, combine=lambda a, b: a + b)


DICT_RIGHT_WINS: Monoid[Dict[str, object]] = Monoid(empty=dict, combine=lambda a, b: {**a, **b})


def map_monoid(value_m: Monoid[T]) -> Monoid[Dict[str, T]]:
    def empty() -> Dict[str, T]:
        return {}

    def combine(a: Dict[str, T], b: Dict[str, T]) -> Dict[str, T]:
        keys = a.keys() | b.keys()
        out: Dict[str, T] = {}
        for k in keys:
            if k in a and k in b:
                out[k] = value_m.combine(a[k], b[k])
            elif k in a:
                out[k] = a[k]
            else:
                out[k] = b[k]
        return out

    return Monoid(empty, combine)


def product_monoid(m1: Monoid[T], m2: Monoid[U]) -> Monoid[Tuple[T, U]]:
    return Monoid(
        empty=lambda: (m1.empty(), m2.empty()),
        combine=lambda a, b: (m1.combine(a[0], b[0]), m2.combine(a[1], b[1])),
    )


def product3(m1: Monoid[T1], m2: Monoid[T2], m3: Monoid[T3]) -> Monoid[Tuple[T1, T2, T3]]:
    return Monoid(
        empty=lambda: (m1.empty(), m2.empty(), m3.empty()),
        combine=lambda a, b: (
            m1.combine(a[0], b[0]),
            m2.combine(a[1], b[1]),
            m3.combine(a[2], b[2]),
        ),
    )


@dataclass(frozen=True, slots=True)
class Metrics:
    processed: int = 0
    succeeded: int = 0
    latency_sum_ms: float = 0.0
    latency_max_ms: float = 0.0


def _check_finite(x: float) -> float:
    if not math.isfinite(x):
        raise ValueError(f"non-finite metric value: {x}")
    return x


METRICS: Monoid[Metrics] = Monoid(
    empty=Metrics,
    combine=lambda a, b: Metrics(
        processed=a.processed + b.processed,
        succeeded=a.succeeded + b.succeeded,
        latency_sum_ms=_check_finite(a.latency_sum_ms + b.latency_sum_ms),
        latency_max_ms=max(a.latency_max_ms, b.latency_max_ms),
    ),
)


def nonempty_tuple_semigroup() -> Semi[Tuple[T, ...]]:
    return Semi(lambda a, b: a + b)


def dedup_stable_semigroup() -> Semi[Tuple[E, ...]]:
    def combine(a: Tuple[E, ...], b: Tuple[E, ...]) -> Tuple[E, ...]:
        seen: set[E] = set()
        out: List[E] = []
        for e in a + b:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return tuple(out)

    return Semi(combine)


__all__ = [
    "Monoid",
    "Semi",
    "fold",
    "fold_map",
    "tree_reduce",
    "Sum",
    "SUM_INT",
    "LIST_STR",
    "DICT_RIGHT_WINS",
    "map_monoid",
    "product_monoid",
    "product3",
    "Metrics",
    "METRICS",
    "nonempty_tuple_semigroup",
    "dedup_stable_semigroup",
]
