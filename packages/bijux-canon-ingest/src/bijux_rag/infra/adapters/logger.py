# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""Bijux RAG infra: log sinks (console + test collector)."""

from __future__ import annotations

from contextlib import suppress

from bijux_rag.domain.capabilities import Logger
from bijux_rag.domain.logging import LogEntry


class ConsoleLogger(Logger):
    def log(self, entry: LogEntry) -> None:
        with suppress(OSError):
            print(f"[{entry.level}] {entry.msg}")


class CollectingLogger(Logger):
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


__all__ = ["ConsoleLogger", "CollectingLogger"]
