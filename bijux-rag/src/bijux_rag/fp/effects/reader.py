# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: Reader – explicit, injectable configuration dependency (effects).

Reader encodes read-only environment access as a pure value:
`Reader[C, T]` is a function `C -> T` with lawful `map` and `and_then`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

C = TypeVar("C")
T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Reader(Generic[C, T]):
    run: Callable[[C], T]

    def map(self, f: Callable[[T], U]) -> "Reader[C, U]":
        return Reader(lambda cfg: f(self.run(cfg)))

    def and_then(self, f: Callable[[T], "Reader[C, U]"]) -> "Reader[C, U]":
        return Reader(lambda cfg: f(self.run(cfg)).run(cfg))


def pure(x: T) -> Reader[C, T]:
    return Reader(lambda _: x)


def ask() -> Reader[C, C]:
    return Reader(lambda cfg: cfg)


def asks(selector: Callable[[C], T]) -> Reader[C, T]:
    return Reader(lambda cfg: selector(cfg))


def local(modify: Callable[[C], C], r: Reader[C, T]) -> Reader[C, T]:
    return Reader(lambda cfg: r.run(modify(cfg)))


__all__ = ["Reader", "pure", "ask", "asks", "local"]
