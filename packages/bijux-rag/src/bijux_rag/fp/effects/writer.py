# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG–07: Writer – accumulate logs/metrics as pure data (effects).

Bijux RAG generalises the Writer log entry type to support structured logs
(e.g. `domain.logging.LogEntry`) while preserving the Bijux RAG API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Tuple, TypeAlias, TypeVar

from bijux_rag.result.types import Err, Ok, Result

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
LogEntryT = TypeVar("LogEntryT")
Log: TypeAlias = Tuple[LogEntryT, ...]
StrLogEntry: TypeAlias = str
StrLog: TypeAlias = tuple[str, ...]


@dataclass(frozen=True)
class Writer(Generic[T, LogEntryT]):
    run: Callable[[], Tuple[T, Log[LogEntryT]]]

    def map(self, f: Callable[[T], U]) -> "Writer[U, LogEntryT]":
        def _run() -> Tuple[U, Log[LogEntryT]]:
            value, log = self.run()
            return f(value), log

        return Writer(_run)

    def and_then(self, f: Callable[[T], "Writer[U, LogEntryT]"]) -> "Writer[U, LogEntryT]":
        def _run() -> Tuple[U, Log[LogEntryT]]:
            value, log1 = self.run()
            next_value, log2 = f(value).run()
            return next_value, log1 + log2

        return Writer(_run)


def pure(x: T) -> Writer[T, LogEntryT]:
    return Writer(lambda: (x, ()))


def tell(entry: LogEntryT) -> Writer[None, LogEntryT]:
    return Writer(lambda: (None, (entry,)))


def tell_many(entries: Log[LogEntryT]) -> Writer[None, LogEntryT]:
    return Writer(lambda: (None, entries))


def listen(p: Writer[T, LogEntryT]) -> Writer[Tuple[T, Log[LogEntryT]], LogEntryT]:
    def _run() -> Tuple[Tuple[T, Log[LogEntryT]], Log[LogEntryT]]:
        value, log = p.run()
        return (value, log), log

    return Writer(_run)


def censor(
    f: Callable[[Log[LogEntryT]], Log[LogEntryT]],
    p: Writer[T, LogEntryT],
) -> Writer[T, LogEntryT]:
    def _run() -> Tuple[T, Log[LogEntryT]]:
        value, log = p.run()
        return value, f(log)

    return Writer(_run)


def run_writer(p: Writer[T, LogEntryT]) -> Tuple[T, Log[LogEntryT]]:
    return p.run()


def wr_pure(x: T) -> Writer[Result[T, E], LogEntryT]:
    return Writer(lambda: (Ok(x), ()))


def wr_map(
    p: Writer[Result[T, E], LogEntryT],
    f: Callable[[T], U],
) -> Writer[Result[U, E], LogEntryT]:
    def _run() -> Tuple[Result[U, E], Log[LogEntryT]]:
        r, log = p.run()
        return r.map(f), log

    return Writer(_run)


def wr_and_then(
    p: Writer[Result[T, E], LogEntryT],
    k: Callable[[T], Writer[Result[U, E], LogEntryT]],
) -> Writer[Result[U, E], LogEntryT]:
    def _run() -> Tuple[Result[U, E], Log[LogEntryT]]:
        r, log1 = p.run()
        if isinstance(r, Err):
            return Err(r.error), log1
        next_r, log2 = k(r.value).run()
        return next_r, log1 + log2

    return Writer(_run)


__all__ = [
    "Log",
    "StrLogEntry",
    "StrLog",
    "Writer",
    "pure",
    "tell",
    "tell_many",
    "listen",
    "censor",
    "run_writer",
    "wr_pure",
    "wr_map",
    "wr_and_then",
]
