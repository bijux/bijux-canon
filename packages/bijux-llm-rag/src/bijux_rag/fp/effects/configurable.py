# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: runtime-configurable pipelines via higher-order combinators (effects)."""

from __future__ import annotations

from typing import Callable, TypeVar

from bijux_rag.result.types import Result

from .writer import Writer, tell

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
A = TypeVar("A")
M = TypeVar("M")


def toggle_validation(
    enabled: bool,
    validate: Callable[[T], Result[T, E]],
    pipeline: Callable[[T], Result[U, E]],
) -> Callable[[T], Result[U, E]]:
    if not enabled:
        return pipeline
    return lambda x: validate(x).and_then(pipeline)


def toggle_logging(
    enabled: bool,
    pipeline: Callable[[T], A],
    mk_msg: Callable[[T, A], str] | None = None,
) -> Callable[[T], Writer[A, str]]:
    if not enabled:
        return lambda x: Writer(lambda: (pipeline(x), ()))

    msg = mk_msg or (lambda x, _: f"processing {x}")

    def wrapped(x: T) -> Writer[A, str]:
        value = pipeline(x)
        return tell(msg(x, value)).map(lambda _: value)

    return wrapped


def toggle_metrics(
    enabled: bool,
    measure: Callable[[T, A], M],
    zero: M,
    pipeline: Callable[[T], A],
) -> Callable[[T], tuple[A, M]]:
    if not enabled:
        return lambda x: (pipeline(x), zero)

    def wrapped(x: T) -> tuple[A, M]:
        value = pipeline(x)
        return value, measure(x, value)

    return wrapped


__all__ = ["toggle_validation", "toggle_logging", "toggle_metrics"]
