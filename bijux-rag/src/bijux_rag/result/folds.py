# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Aggregation folds over Result streams (end-of-Bijux RAG)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, TypeVar

from .types import Err, Ok, Result

T = TypeVar("T")
E = TypeVar("E")
A = TypeVar("A")


def fold_results_fail_fast(
    xs: Iterable[Result[T, E]], init: A, fn: Callable[[A, T], A]
) -> Result[A, E]:
    """Aggregate Ok values with fn; short-circuit on first Err. Laziness preserved."""

    acc = init
    for r in xs:
        if isinstance(r, Err):
            return Err(r.error)
        acc = fn(acc, r.value)
    return Ok(acc)


def fold_results_collect_errs(
    xs: Iterable[Result[T, E]], init: A, fn: Callable[[A, T], A]
) -> Result[A, list[E]]:
    """All-or-nothing accumulation: any Err => Err(all errors). Consumes entire finite stream."""

    acc = init
    errs: list[E] = []
    for r in xs:
        if isinstance(r, Err):
            errs.append(r.error)
        else:
            acc = fn(acc, r.value)
    return Err(errs) if errs else Ok(acc)


def fold_results_collect_errs_capped(
    xs: Iterable[Result[T, E]],
    init: A,
    fn: Callable[[A, T], A],
    *,
    max_errs: int,
) -> Result[A, tuple[list[E], bool]]:
    """All-or-nothing accumulation with error cap and overflow flag. Consumes entire finite stream."""

    acc = init
    errs: list[E] = []
    capped = False
    for r in xs:
        if isinstance(r, Err):
            if len(errs) < max_errs:
                errs.append(r.error)
            else:
                capped = True
        else:
            acc = fn(acc, r.value)
    return Err((errs, capped)) if errs or capped else Ok(acc)


def fold_until_error_rate(
    xs: Iterable[Result[T, E]],
    init: A,
    fn: Callable[[A, T], A],
    *,
    max_rate: float,
    min_samples: int = 100,
) -> Result[A, tuple[E, float, int]]:
    """Aggregate until error rate exceeds max_rate after min_samples, returning last error and stats."""

    if not 0.0 < max_rate < 1.0:
        raise ValueError("max_rate must be in (0,1)")
    if min_samples < 1:
        raise ValueError("min_samples >= 1")

    acc = init
    n_ok = n_err = 0
    last_err: E | None = None
    for r in xs:
        if isinstance(r, Ok):
            acc = fn(acc, r.value)
            n_ok += 1
        else:
            last_err = r.error
            n_err += 1
        total = n_ok + n_err
        if total >= min_samples and n_err / total > max_rate:
            assert last_err is not None
            return Err((last_err, n_err / total, total))
    return Ok(acc)


def all_ok_fail_fast(xs: Iterable[Result[T, E]]) -> Result[list[T], E]:
    """Collect all Ok values; short-circuit on first Err."""

    acc: list[T] = []
    for r in xs:
        if isinstance(r, Err):
            return Err(r.error)
        acc.append(r.value)
    return Ok(acc)


@dataclass(frozen=True)
class ResultsBoth(Generic[T, E]):
    oks: list[T]
    errs: list[E]


def collect_both(xs: Iterable[Result[T, E]]) -> ResultsBoth[T, E]:
    """Collect all Ok values and all Err errors. Consumes entire finite stream."""

    oks: list[T] = []
    errs: list[E] = []
    for r in xs:
        if isinstance(r, Ok):
            oks.append(r.value)
        else:
            errs.append(r.error)
    return ResultsBoth(oks, errs)


__all__ = [
    "ResultsBoth",
    "fold_results_fail_fast",
    "fold_results_collect_errs",
    "fold_results_collect_errs_capped",
    "fold_until_error_rate",
    "all_ok_fail_fast",
    "collect_both",
]
