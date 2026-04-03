# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Composable iterator stages and demand fencing (Bijux RAG)."""

from __future__ import annotations

from itertools import islice
from typing import Any, Callable, Iterable, Iterator, TypeVar

from .types import Source, Transform

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
T = TypeVar("T")


def fence_k(k: int) -> Transform[A, A]:
    """Stage that yields at most the first k items (hard cap)."""

    if k < 0:
        raise ValueError("k must be >= 0")

    def stage(items: Iterable[A]) -> Iterator[A]:
        yield from islice(items, k)

    return stage


def compose2_transforms(s1: Transform[A, B], s2: Transform[B, C]) -> Transform[A, C]:
    """Compose two iterable transforms left-to-right."""

    def stage(items: Iterable[A]) -> Iterator[C]:
        return s2(s1(items))

    return stage


def compose_transforms(
    *stages: Callable[[Iterable[Any]], Iterator[Any]],
) -> Callable[[Iterable[Any]], Iterator[Any]]:
    """Compose iterable transforms left-to-right (loose typing; intended for ergonomics)."""

    if not stages:
        raise ValueError("compose_transforms needs at least one stage")

    def stage(items: Iterable[Any]) -> Iterator[Any]:
        out: Iterable[Any] = items
        for s in stages:
            out = s(out)
        return iter(out)

    return stage


def source_to_transform(src: Source[T]) -> Transform[None, T]:
    """Adapt a Source[T] to a Transform[None, T] (useful with compose_transforms)."""

    def stage(_: Iterable[None]) -> Iterator[T]:
        yield from src()

    return stage


__all__ = ["fence_k", "compose2_transforms", "compose_transforms", "source_to_transform"]
