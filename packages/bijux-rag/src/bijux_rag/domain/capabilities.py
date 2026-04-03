# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: capability protocols – typed effect interfaces (mypy --strict)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Protocol

from bijux_rag.core.rag_types import Chunk, RawDoc
from bijux_rag.result.types import ErrInfo, Option, Result

from .logging import LogEntry

__all__ = [
    "StorageRead",
    "StorageWrite",
    "Storage",
    "Clock",
    "Logger",
    "Cache",
]


class StorageRead(Protocol):
    def read_docs(self, path: str) -> Iterator[Result[RawDoc, ErrInfo]]: ...


class StorageWrite(Protocol):
    def write_chunks(self, path: str, chunks: Iterator[Chunk]) -> Result[None, ErrInfo]: ...


class Storage(StorageRead, StorageWrite, Protocol):
    """Composed capability: full read/write access."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class Logger(Protocol):
    def log(self, entry: LogEntry) -> None: ...


class Cache(Protocol):
    def get(self, key: str) -> Result[Option[Chunk], ErrInfo]: ...

    def set(self, key: str, chunk: Chunk) -> Result[None, ErrInfo]: ...
