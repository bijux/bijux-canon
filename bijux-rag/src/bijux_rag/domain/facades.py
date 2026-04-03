# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 8: functional facades for imperative libraries (end-of-Bijux RAG).

This module provides minimal, dependency-free building blocks:
- `Keyed[K, T]` for idempotent/keyed effects
- example ports that return *descriptions* (`IOPlan` / `AsyncPlan`) rather than performing effects
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding
from bijux_rag.domain.effects import IOPlan, io_delay
from bijux_rag.rag.stages import embed_chunk
from bijux_rag.result.types import ErrInfo, Ok, Result

K = TypeVar("K")
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Keyed(Generic[K, T]):
    key: K
    value: T


class EmbedderPort(Protocol):
    """Pure port: returns an IOPlan description, does not perform embedding."""

    def embed_batch(
        self, items: list[Keyed[K, ChunkWithoutEmbedding]]
    ) -> IOPlan[list[Keyed[K, Chunk]]]: ...


def deterministic_embedder_port(
    *,
    embed_one: Callable[[ChunkWithoutEmbedding], Chunk] = embed_chunk,
) -> EmbedderPort:
    """Reference implementation: deterministic embedding, delayed via IOPlan."""

    class _Port(EmbedderPort):
        def embed_batch(
            self, items: list[Keyed[K, ChunkWithoutEmbedding]]
        ) -> IOPlan[list[Keyed[K, Chunk]]]:
            def thunk() -> Result[list[Keyed[K, Chunk]], ErrInfo]:
                out: list[Keyed[K, Chunk]] = []
                for it in items:
                    out.append(Keyed(key=it.key, value=embed_one(it.value)))
                return Ok(out)

            return io_delay(thunk)

    return _Port()


__all__ = ["Keyed", "EmbedderPort", "deterministic_embedder_port"]
