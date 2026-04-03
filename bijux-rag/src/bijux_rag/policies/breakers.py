# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Short-circuiting and circuit breakers for Result streams (end-of-Bijux RAG)."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Generic, Iterable, Iterator, Mapping, TypeVar, cast

from bijux_rag.result import Err, Ok, Result

T = TypeVar("T")
E = TypeVar("E")


def _close_if_possible(it: object) -> None:
    close = getattr(it, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # noqa: BLE001 - never mask the original termination
            pass


@dataclass(frozen=True)
class BreakInfo(Generic[E]):
    code: str
    reason: str
    last_error: E | None
    n_ok: int
    n_err: int
    total: int
    threshold: Mapping[str, object]


def short_circuit_on_err_emit(xs: Iterable[Result[T, E]]) -> Iterator[Result[T, E | BreakInfo[E]]]:
    """Yield items until first Err (which is yielded), then emit terminal BreakInfo."""

    it = iter(xs)
    n_ok = n_err = 0
    last_err: E | None = None
    exhausted = False
    try:
        for r in it:
            yield cast(Result[T, E | BreakInfo[E]], r)
            if isinstance(r, Ok):
                n_ok += 1
            else:
                n_err += 1
                last_err = r.error
                bi = BreakInfo(
                    code="BREAK/FIRST_ERR",
                    reason="first error encountered",
                    last_error=last_err,
                    n_ok=n_ok,
                    n_err=n_err,
                    total=n_ok + n_err,
                    threshold=MappingProxyType({}),
                )
                yield Err(bi)
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def short_circuit_on_err_truncate(xs: Iterable[Result[T, E]]) -> Iterator[Result[T, E]]:
    """Yield until first Err, then stop silently (no terminal value)."""

    it = iter(xs)
    exhausted = False
    try:
        for r in it:
            yield r
            if isinstance(r, Err):
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_rate_emit(
    xs: Iterable[Result[T, E]],
    *,
    max_rate: float,
    min_samples: int = 100,
) -> Iterator[Result[T, E | BreakInfo[E]]]:
    """Yield until error rate > max_rate after min_samples, then emit terminal BreakInfo."""

    if not 0.0 < max_rate < 1.0:
        raise ValueError("max_rate must be in (0,1)")
    if min_samples < 1:
        raise ValueError("min_samples >= 1")

    it = iter(xs)
    n_ok = n_err = 0
    last_err: E | None = None
    exhausted = False
    try:
        for r in it:
            yield cast(Result[T, E | BreakInfo[E]], r)
            if isinstance(r, Ok):
                n_ok += 1
            else:
                n_err += 1
                last_err = r.error
            total = n_ok + n_err
            if total >= min_samples and n_err / total > max_rate:
                bi = BreakInfo(
                    code="BREAK/ERR_RATE",
                    reason=f"error rate {n_err / total:.3f} > {max_rate}",
                    last_error=last_err,
                    n_ok=n_ok,
                    n_err=n_err,
                    total=total,
                    threshold=MappingProxyType({"max_rate": max_rate, "min_samples": min_samples}),
                )
                yield Err(bi)
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_rate_truncate(
    xs: Iterable[Result[T, E]],
    *,
    max_rate: float,
    min_samples: int = 100,
) -> Iterator[Result[T, E]]:
    if not 0.0 < max_rate < 1.0:
        raise ValueError("max_rate must be in (0,1)")
    if min_samples < 1:
        raise ValueError("min_samples >= 1")

    it = iter(xs)
    n_ok = n_err = 0
    exhausted = False
    try:
        for r in it:
            yield r
            if isinstance(r, Ok):
                n_ok += 1
            else:
                n_err += 1
            total = n_ok + n_err
            if total >= min_samples and n_err / total > max_rate:
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_count_emit(
    xs: Iterable[Result[T, E]], *, max_errs: int
) -> Iterator[Result[T, E | BreakInfo[E]]]:
    """Yield until error count > max_errs, then emit terminal BreakInfo."""

    if max_errs < 0:
        raise ValueError("max_errs >= 0")

    it = iter(xs)
    n_ok = n_err = 0
    last_err: E | None = None
    exhausted = False
    try:
        for r in it:
            yield cast(Result[T, E | BreakInfo[E]], r)
            if isinstance(r, Err):
                n_err += 1
                last_err = r.error
                if n_err > max_errs:
                    bi = BreakInfo(
                        code="BREAK/ERR_COUNT",
                        reason=f"errors {n_err} > {max_errs}",
                        last_error=last_err,
                        n_ok=n_ok,
                        n_err=n_err,
                        total=n_ok + n_err,
                        threshold=MappingProxyType({"max_errs": max_errs}),
                    )
                    yield Err(bi)
                    return
            else:
                n_ok += 1
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_count_truncate(
    xs: Iterable[Result[T, E]], *, max_errs: int
) -> Iterator[Result[T, E]]:
    if max_errs < 0:
        raise ValueError("max_errs >= 0")

    it = iter(xs)
    n_err = 0
    exhausted = False
    try:
        for r in it:
            yield r
            if isinstance(r, Err):
                n_err += 1
                if n_err > max_errs:
                    return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_pred_emit(
    xs: Iterable[Result[T, E]],
    pred: Callable[[Result[T, E]], bool],
) -> Iterator[Result[T, E | BreakInfo[E]]]:
    """Yield until pred(r) is True, then emit terminal BreakInfo."""

    it = iter(xs)
    n_ok = n_err = 0
    last_err: E | None = None
    exhausted = False
    try:
        for r in it:
            yield cast(Result[T, E | BreakInfo[E]], r)
            if isinstance(r, Ok):
                n_ok += 1
            else:
                n_err += 1
                last_err = r.error
            if pred(r):
                bi = BreakInfo(
                    code="BREAK/PRED",
                    reason="predicate triggered",
                    last_error=last_err,
                    n_ok=n_ok,
                    n_err=n_err,
                    total=n_ok + n_err,
                    threshold=MappingProxyType({}),
                )
                yield Err(bi)
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


def circuit_breaker_pred_truncate(
    xs: Iterable[Result[T, E]], pred: Callable[[Result[T, E]], bool]
) -> Iterator[Result[T, E]]:
    it = iter(xs)
    exhausted = False
    try:
        for r in it:
            yield r
            if pred(r):
                return
        exhausted = True
    finally:
        if not exhausted:
            _close_if_possible(it)


__all__ = [
    "BreakInfo",
    "short_circuit_on_err_emit",
    "short_circuit_on_err_truncate",
    "circuit_breaker_rate_emit",
    "circuit_breaker_rate_truncate",
    "circuit_breaker_count_emit",
    "circuit_breaker_count_truncate",
    "circuit_breaker_pred_emit",
    "circuit_breaker_pred_truncate",
]
