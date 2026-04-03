# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: structured logging as pure data (LogEntry + Writer).

This module defines the *domain-owned* structured log entry type (`LogEntry`) and
small helpers that produce `Writer[..., LogEntry]` values.

The Writer container itself is a generic effect encoding and lives in
`bijux_rag.fp.effects.writer`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias, TypeVar

from bijux_rag.fp.effects.writer import Writer, tell

Level: TypeAlias = Literal["INFO", "DEBUG", "TRACE", "ERROR"]


@dataclass(frozen=True, slots=True)
class LogEntry:
    level: Level
    msg: str


Logs: TypeAlias = tuple[LogEntry, ...]
T = TypeVar("T")


class LogMonoid:
    @staticmethod
    def empty() -> Logs:
        return ()

    @staticmethod
    def append(left: Logs, right: Logs) -> Logs:
        return left + right


def log_tell(entry: LogEntry) -> Writer[None, LogEntry]:
    return tell(entry)


def trace_stage(msg: str, level: Level = "INFO") -> Writer[None, LogEntry]:
    return log_tell(LogEntry(level=level, msg=msg))


def trace_value(name: str, value: object, level: Level = "DEBUG") -> Writer[None, LogEntry]:
    return log_tell(LogEntry(level=level, msg=f"{name}={value!r}"))


__all__ = ["Level", "LogEntry", "Logs", "LogMonoid", "log_tell", "trace_stage", "trace_value"]
