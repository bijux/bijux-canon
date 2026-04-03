# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: exception bridging helpers (use only at effect boundaries; adapters).

Expected domain errors should be represented as `Result` / `Validation` values.
Unexpected failures (bugs) should raise and crash early.

These helpers intentionally focus on *boundary* use: the caller supplies an
`exc_type` that defines what is considered "expected".
"""

from __future__ import annotations

from typing import Callable, NoReturn, TypeAlias, TypeVar

from bijux_rag.fp.core import Validation, VFailure, VSuccess
from bijux_rag.result.types import Err, Ok, Result

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")

ExcTypes: TypeAlias = type[Exception] | tuple[type[Exception], ...]


def try_result(
    thunk: Callable[[], T],
    map_exc: Callable[[Exception], E],
    exc_type: ExcTypes = Exception,
) -> Result[T, E]:
    """Bridge an impure thunk into Result.

    Only exceptions matching `exc_type` are treated as expected domain errors.
    Everything else propagates as a bug (never becomes Err).
    """

    try:
        return Ok(thunk())
    except exc_type as ex:
        return Err(map_exc(ex))


def result_map_try(
    r: Result[T, E],
    f: Callable[[T], U],
    map_exc: Callable[[Exception], E],
    exc_type: ExcTypes = Exception,
) -> Result[U, E]:
    """Apply a possibly-throwing `f` to a successful Result (boundary-only)."""

    if isinstance(r, Err):
        return Err(r.error)
    try:
        return Ok(f(r.value))
    except exc_type as ex:
        return Err(map_exc(ex))


def v_try(
    thunk: Callable[[], T],
    map_exc: Callable[[Exception], E],
    exc_type: ExcTypes = Exception,
) -> Validation[T, E]:
    """Bridge an impure thunk into Validation (boundary-only).

    Exceptions become a single `VFailure`. Accumulation happens only when you
    combine multiple Validations applicatively.
    """

    try:
        return VSuccess(thunk())
    except exc_type as ex:
        return VFailure((map_exc(ex),))


def v_map_try(
    v: Validation[T, E],
    f: Callable[[T], U],
    map_exc: Callable[[Exception], E],
    exc_type: ExcTypes = Exception,
) -> Validation[U, E]:
    """Apply a possibly-throwing `f` to a successful Validation (boundary-only)."""

    if isinstance(v, VFailure):
        return v
    try:
        return VSuccess(f(v.value))
    except exc_type as ex:
        return VFailure((map_exc(ex),))


class UnexpectedFailure(RuntimeError):
    """Raised by `unexpected_fail` for unrecoverable outer-boundary states."""


def unexpected_fail(msg: str) -> NoReturn:
    raise UnexpectedFailure(msg)


__all__ = [
    "try_result",
    "result_map_try",
    "v_try",
    "v_map_try",
    "UnexpectedFailure",
    "unexpected_fail",
]
