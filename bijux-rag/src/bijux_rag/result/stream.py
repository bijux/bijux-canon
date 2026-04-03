# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Streaming combinators for Result-valued pipelines (end-of-Bijux RAG)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar

from .types import Err, ErrInfo, Ok, Result, make_errinfo

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


def map_result_iter(f: Callable[[T], Result[U, E]], xs: Iterable[T]) -> Iterator[Result[U, E]]:
    for x in xs:
        yield f(x)


def filter_ok(xs: Iterable[Result[T, E]]) -> Iterator[T]:
    for r in xs:
        if isinstance(r, Ok):
            yield r.value


def filter_err(xs: Iterable[Result[T, E]]) -> Iterator[E]:
    for r in xs:
        if isinstance(r, Err):
            yield r.error


def partition_results(xs: Iterable[Result[T, E]]) -> tuple[list[T], list[E]]:
    oks: list[T] = []
    errs: list[E] = []
    for r in xs:
        if isinstance(r, Ok):
            oks.append(r.value)
        else:
            errs.append(r.error)
    return oks, errs


def try_map_iter(
    fn: Callable[[T], U],
    xs: Iterable[T],
    *,
    stage: str,
    key_path: Callable[[T], tuple[int, ...]] | None = None,
    code: str = "PIPE/EXC",
) -> Iterator[Result[U, ErrInfo]]:
    for x in xs:
        try:
            yield Ok(fn(x))
        except Exception as exc:  # noqa: BLE001 - pipeline combinator intentionally catches
            p = key_path(x) if key_path is not None else ()
            yield Err(make_errinfo(code, str(exc), stage, p, exc))


def par_try_map_iter(
    fn: Callable[[T], U],
    xs: Iterable[T],
    *,
    stage: str,
    key_path: Callable[[T], tuple[int, ...]] | None = None,
    code: str = "PIPE/EXC",
    max_workers: int = 8,
    max_in_flight: int = 32,
) -> Iterator[Result[U, ErrInfo]]:
    it = iter(xs)
    inflight: deque[tuple[int, T, Future[U]]] = deque()
    idx = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        while len(inflight) < max_in_flight:
            try:
                x = next(it)
            except StopIteration:
                break
            inflight.append((idx, x, ex.submit(fn, x)))
            idx += 1

        out_idx = 0
        while inflight:
            while inflight and inflight[0][0] == out_idx:
                _, x, fut = inflight.popleft()
                try:
                    yield Ok(fut.result())
                except Exception as exc:  # noqa: BLE001 - pipeline combinator intentionally catches
                    p = key_path(x) if key_path is not None else ()
                    yield Err(make_errinfo(code, str(exc), stage, p, exc))
                out_idx += 1

            if len(inflight) < max_in_flight:
                try:
                    x = next(it)
                except StopIteration:
                    continue
                inflight.append((idx, x, ex.submit(fn, x)))
                idx += 1


def tap_ok(xs: Iterable[Result[T, E]], fn: Callable[[T], None]) -> Iterator[Result[T, E]]:
    for r in xs:
        if isinstance(r, Ok):
            fn(r.value)
        yield r


def tap_err(xs: Iterable[Result[T, E]], fn: Callable[[E], None]) -> Iterator[Result[T, E]]:
    for r in xs:
        if isinstance(r, Err):
            fn(r.error)
        yield r


def recover_iter(xs: Iterable[Result[T, E]], fn: Callable[[E], T]) -> Iterator[T]:
    for r in xs:
        yield r.value if isinstance(r, Ok) else fn(r.error)


def recover_result_iter(
    xs: Iterable[Result[T, E]], fn: Callable[[E], Result[T, E]]
) -> Iterator[Result[T, E]]:
    for r in xs:
        yield r if isinstance(r, Ok) else fn(r.error)


def split_results_to_sinks(
    xs: Iterable[Result[T, E]], on_ok: Callable[[T], None], on_err: Callable[[E], None]
) -> None:
    for r in xs:
        if isinstance(r, Ok):
            on_ok(r.value)
        else:
            on_err(r.error)


def split_results_to_sinks_guarded(
    xs: Iterable[Result[T, E]],
    on_ok: Callable[[T], None],
    on_err: Callable[[E], None],
    *,
    stage: str = "sink",
) -> Iterator[Result[None, ErrInfo]]:
    for r in xs:
        try:
            if isinstance(r, Ok):
                on_ok(r.value)
            else:
                on_err(r.error)
            yield Ok(None)
        except Exception as exc:  # noqa: BLE001 - sink guards intentionally catch
            yield Err(make_errinfo("SINK/EXC", str(exc), stage, (), exc))


__all__ = [
    "map_result_iter",
    "filter_ok",
    "filter_err",
    "partition_results",
    "try_map_iter",
    "par_try_map_iter",
    "tap_ok",
    "tap_err",
    "recover_iter",
    "recover_result_iter",
    "split_results_to_sinks",
    "split_results_to_sinks_guarded",
]
