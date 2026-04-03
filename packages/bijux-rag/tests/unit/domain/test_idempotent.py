# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from collections.abc import Iterator

from bijux_rag.core.rag_types import Chunk
from bijux_rag.domain.effects.io_plan import perform
from bijux_rag.domain.idempotent import AtomicWriteCap, content_key, idempotent_write
from bijux_rag.result.types import ErrInfo, Ok, Result


def _chunk(text: str) -> Chunk:
    return Chunk(
        doc_id="d1",
        text=text,
        start=0,
        end=len(text),
        metadata={"k": "v"},
        embedding=tuple([0.0] * 16),
    )


def test_content_key_depends_only_on_text() -> None:
    a1 = _chunk("alpha")
    a2 = Chunk(
        doc_id="d2",
        text="alpha",
        start=10,
        end=15,
        metadata={"different": True},
        embedding=tuple([1.0] * 16),
    )
    assert content_key(iter([a1])) == content_key(iter([a2]))


def test_idempotent_write_writes_at_most_once() -> None:
    class FakeAtomic(AtomicWriteCap):
        def __init__(self) -> None:
            self.present: set[str] = set()
            self.write_attempts: int = 0
            self.actual_writes: int = 0

        def write_if_absent(self, key: str, chunks: Iterator[Chunk]) -> Result[bool, ErrInfo]:
            self.write_attempts += 1
            if key in self.present:
                return Ok(False)
            self.present.add(key)
            self.actual_writes += 1
            list(chunks)  # consume
            return Ok(True)

    atomic = FakeAtomic()
    write = idempotent_write(atomic)
    chunks = [_chunk("a"), _chunk("b")]

    r1 = perform(write(iter(chunks)))
    r2 = perform(write(iter(chunks)))

    assert r1 == Ok(Ok(None))
    assert r2 == Ok(Ok(None))
    assert atomic.write_attempts == 2
    assert atomic.actual_writes == 1
