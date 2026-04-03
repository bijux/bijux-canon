# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: idempotent effect design for safe retries/replays."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from hashlib import sha256
from typing import Protocol, TypeVar

from bijux_rag.core.rag_types import Chunk
from bijux_rag.domain.effects.io_plan import IOPlan, io_delay
from bijux_rag.result.types import Err, ErrInfo, Ok, Result

T = TypeVar("T")


class AtomicWriteCap(Protocol):
    def write_if_absent(self, key: str, chunks: Iterator[Chunk]) -> Result[bool, ErrInfo]:
        """Return Ok(True) if written; Ok(False) if already present."""


def content_key(chunks: Iterator[Chunk]) -> str:
    """Stable, length-prefixed hash over chunk text."""

    h = sha256()
    for c in chunks:
        text = c.text
        h.update(str(len(text)).encode("utf-8"))
        h.update(b"\0")
        h.update(text.encode("utf-8"))
    return h.hexdigest()


def idempotent_write(
    atomic: AtomicWriteCap,
) -> Callable[[Iterator[Chunk]], IOPlan[Result[None, ErrInfo]]]:
    """Idempotent write behaviour built on an atomic write-if-absent capability."""

    def behaviour(chunks: Iterator[Chunk]) -> IOPlan[Result[None, ErrInfo]]:
        cs = list(chunks)
        key = content_key(iter(cs))

        def act() -> Result[Result[None, ErrInfo], ErrInfo]:
            wrote = atomic.write_if_absent(key, iter(cs))
            if isinstance(wrote, Err):
                return Ok(Err(wrote.error))
            return Ok(Ok(None))

        return io_delay(act)

    return behaviour


__all__ = ["AtomicWriteCap", "content_key", "idempotent_write"]
