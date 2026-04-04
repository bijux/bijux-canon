# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Writer helpers for accumulating logs and metrics as pure data.

The Writer log entry type supports structured records such as
`domain.logging.LogEntry` while keeping the public API stable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

from bijux_canon_ingest.result.types import Err, Ok, Result

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")
LogEntryT = TypeVar("LogEntryT")
Log: TypeAlias = tuple[LogEntryT, ...]
StrLogEntry: TypeAlias = str
StrLog: TypeAlias = tuple[str, ...]


@dataclass(frozen=True)
class Writer(Generic[T, LogEntryT]):
    run: Callable[[], tuple[T, Log[LogEntryT]]]

    def map(self, f: Callable[[T], U]) -> Writer[U, LogEntryT]:
        def _run() -> tuple[U, Log[LogEntryT]]:
            value, log = self.run()
            return f(value), log

        return Writer(_run)

    def and_then(self, f: Callable[[T], Writer[U, LogEntryT]]) -> Writer[U, LogEntryT]:
        def _run() -> tuple[U, Log[LogEntryT]]:
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


def listen(p: Writer[T, LogEntryT]) -> Writer[tuple[T, Log[LogEntryT]], LogEntryT]:
    def _run() -> tuple[tuple[T, Log[LogEntryT]], Log[LogEntryT]]:
        value, log = p.run()
        return (value, log), log

    return Writer(_run)


def censor(
    f: Callable[[Log[LogEntryT]], Log[LogEntryT]],
    p: Writer[T, LogEntryT],
) -> Writer[T, LogEntryT]:
    def _run() -> tuple[T, Log[LogEntryT]]:
        value, log = p.run()
        return value, f(log)

    return Writer(_run)


def run_writer(p: Writer[T, LogEntryT]) -> tuple[T, Log[LogEntryT]]:
    return p.run()


def wr_pure(x: T) -> Writer[Result[T, E], LogEntryT]:
    return Writer(lambda: (Ok(x), ()))


def wr_map(
    p: Writer[Result[T, E], LogEntryT],
    f: Callable[[T], U],
) -> Writer[Result[U, E], LogEntryT]:
    def _run() -> tuple[Result[U, E], Log[LogEntryT]]:
        r, log = p.run()
        return r.map(f), log

    return Writer(_run)


def wr_and_then(
    p: Writer[Result[T, E], LogEntryT],
    k: Callable[[T], Writer[Result[U, E], LogEntryT]],
) -> Writer[Result[U, E], LogEntryT]:
    def _run() -> tuple[Result[U, E], Log[LogEntryT]]:
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
