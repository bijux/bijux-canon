# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: IOPlan – deferred, composable IO as data (domain).

`IOPlan[A]` is a pure *description* of an effect that yields a `Result[A, ErrInfo]`
when interpreted by the shell via `perform`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from bijux_rag.result.types import Err, ErrInfo, Ok, Result

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class IOPlan(Generic[A]):
    thunk: Callable[[], Result[A, ErrInfo]]


def io_pure(value: A) -> IOPlan[A]:
    return IOPlan(lambda: Ok(value))


def io_delay(thunk: Callable[[], Result[A, ErrInfo]]) -> IOPlan[A]:
    return IOPlan(thunk)


def io_bind(plan: IOPlan[A], f: Callable[[A], IOPlan[B]]) -> IOPlan[B]:
    def thunk() -> Result[B, ErrInfo]:
        res = plan.thunk()
        if isinstance(res, Err):
            return Err(res.error)
        return f(res.value).thunk()

    return IOPlan(thunk)


def io_map(plan: IOPlan[A], f: Callable[[A], B]) -> IOPlan[B]:
    return io_bind(plan, lambda x: io_pure(f(x)))


def perform(plan: IOPlan[A]) -> Result[A, ErrInfo]:
    return plan.thunk()


__all__ = ["IOPlan", "io_pure", "io_delay", "io_bind", "io_map", "perform"]
