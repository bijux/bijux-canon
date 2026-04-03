# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bijux RAG: State – explicit, threaded local state without mutation (effects)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class State(Generic[S, T]):
    run: Callable[[S], tuple[T, S]]

    def map(self, f: Callable[[T], U]) -> State[S, U]:
        def _run(s: S) -> tuple[U, S]:
            value, new_s = self.run(s)
            return f(value), new_s

        return State(_run)

    def and_then(self, f: Callable[[T], State[S, U]]) -> State[S, U]:
        def _run(s: S) -> tuple[U, S]:
            value, new_s = self.run(s)
            return f(value).run(new_s)

        return State(_run)


def pure(x: T) -> State[S, T]:
    return State(lambda s: (x, s))


def get() -> State[S, S]:
    return State(lambda s: (s, s))


def put(new_s: S) -> State[S, None]:
    return State(lambda _: (None, new_s))


def modify(f: Callable[[S], S]) -> State[S, None]:
    return State(lambda s: (None, f(s)))


def run_state(p: State[S, T], initial: S) -> tuple[T, S]:
    return p.run(initial)


__all__ = ["State", "pure", "get", "put", "modify", "run_state"]
