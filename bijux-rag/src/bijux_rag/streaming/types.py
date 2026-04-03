# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Streaming type aliases and small trace helpers (Bijux RAG)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
A = TypeVar("A")
B = TypeVar("B")
A_lens = TypeVar("A_lens", contravariant=True)

Source = Callable[[], Iterator[T]]
Transform = Callable[[Iterable[A]], Iterator[B]]


class Lens(Protocol, Generic[A_lens]):
    def note(self, item: A_lens) -> None: ...


@dataclass
class TraceLens(Generic[T]):
    """Bounded stream trace: counts all items and stores a bounded sample prefix."""

    limit: int = 5
    samples: list[T] = field(default_factory=list)
    count: int = 0

    def note(self, item: T) -> None:
        self.count += 1
        if len(self.samples) < self.limit:
            self.samples.append(item)


def trace_iter(items: Iterable[T], lens: Lens[T]) -> Iterator[T]:
    """Yield items unchanged while recording via the provided lens."""

    for item in items:
        lens.note(item)
        yield item


__all__ = ["Source", "Transform", "Lens", "TraceLens", "trace_iter"]
