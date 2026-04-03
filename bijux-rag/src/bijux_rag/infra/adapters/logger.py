# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG infra: log sinks (console + test collector)."""

from __future__ import annotations

from bijux_rag.domain.capabilities import Logger
from bijux_rag.domain.logging import LogEntry


class ConsoleLogger(Logger):
    def log(self, entry: LogEntry) -> None:
        try:
            print(f"[{entry.level}] {entry.msg}")
        except OSError:
            pass


class CollectingLogger(Logger):
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def log(self, entry: LogEntry) -> None:
        self.entries.append(entry)


__all__ = ["ConsoleLogger", "CollectingLogger"]
