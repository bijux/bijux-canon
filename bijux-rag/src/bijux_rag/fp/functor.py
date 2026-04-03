# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG functors: curried mapping over Option, Result, and sequences (end-of-Bijux RAG)."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Optional, Tuple, TypeVar, cast

from .core import NONE, Err, ErrInfo, Ok, Option, Result, Some, make_errinfo

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
E = TypeVar("E")
F = TypeVar("F")


def compose(f: Callable[[T], U], g: Callable[[U], V]) -> Callable[[T], V]:
    return lambda x: g(f(x))


def option_map(f: Callable[[T], U]) -> Callable[[Option[T]], Option[U]]:
    def _inner(opt: Option[T]) -> Option[U]:
        return Some(value=f(opt.value)) if isinstance(opt, Some) else NONE

    return _inner


def from_optional(x: Optional[T]) -> Option[T]:
    return NONE if x is None else Some(value=x)


def to_optional(opt: Option[T]) -> Optional[T]:
    return opt.value if isinstance(opt, Some) else None


def result_map(f: Callable[[T], U]) -> Callable[[Result[T, E]], Result[U, E]]:
    def _inner(res: Result[T, E]) -> Result[U, E]:
        if isinstance(res, Ok):
            return Ok(f(res.value))
        return cast(Result[U, E], res)

    return _inner


def result_try_map(
    f: Callable[[T], U],
    *,
    stage: str = "",
    path: Tuple[int, ...] = (),
) -> Callable[[Result[T, ErrInfo]], Result[U, ErrInfo]]:
    def _inner(res: Result[T, ErrInfo]) -> Result[U, ErrInfo]:
        if isinstance(res, Err):
            return Err(res.error)
        try:
            return Ok(f(res.value))
        except Exception as exc:
            return Err(
                make_errinfo(
                    code="EXC",
                    msg=str(exc),
                    stage=stage,
                    path=path,
                    exc=exc,
                    meta={"exc_type": type(exc).__name__},
                )
            )

    return _inner


def result_map_err(f: Callable[[E], F]) -> Callable[[Result[T, E]], Result[T, F]]:
    def _inner(res: Result[T, E]) -> Result[T, F]:
        if isinstance(res, Err):
            return Err(f(res.error))
        return cast(Result[T, F], res)

    return _inner


def result_bimap(
    f: Callable[[T], U], g: Callable[[E], F]
) -> Callable[[Result[T, E]], Result[U, F]]:
    def _inner(res: Result[T, E]) -> Result[U, F]:
        if isinstance(res, Ok):
            return Ok(f(res.value))
        return Err(g(res.error))

    return _inner


def iter_map(f: Callable[[T], U]) -> Callable[[Iterable[T]], Iterator[U]]:
    def _inner(xs: Iterable[T]) -> Iterator[U]:
        for x in xs:
            yield f(x)

    return _inner


def list_map(f: Callable[[T], U]) -> Callable[[Sequence[T]], tuple[U, ...]]:
    def _inner(xs: Sequence[T]) -> tuple[U, ...]:
        return tuple(iter_map(f)(xs))

    return _inner


__all__ = [
    "Option",
    "Some",
    "NONE",
    "option_map",
    "from_optional",
    "to_optional",
    "result_map",
    "result_try_map",
    "result_map_err",
    "result_bimap",
    "iter_map",
    "list_map",
    "compose",
]
