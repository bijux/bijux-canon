# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Domain-owned ports for keyed embedding workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from bijux_canon_ingest.core.types import Chunk, ChunkWithoutEmbedding
from bijux_canon_ingest.domain.effects import IOPlan, io_delay
from bijux_canon_ingest.result.types import ErrInfo, Ok, Result

K = TypeVar("K")
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Keyed(Generic[K, T]):
    key: K
    value: T


class EmbedderPort(Protocol):
    """Pure port that returns an ``IOPlan`` description rather than performing embedding."""

    def embed_batch(
        self, items: list[Keyed[K, ChunkWithoutEmbedding]]
    ) -> IOPlan[list[Keyed[K, Chunk]]]: ...


def deterministic_embedder_port(
    *,
    embed_one: Callable[[ChunkWithoutEmbedding], Chunk] | None = None,
) -> EmbedderPort:
    """Return a deterministic port that delays embedding work behind ``IOPlan``."""

    if embed_one is None:
        from bijux_canon_ingest.processing.stages import (
            embed_chunk as default_embed_one,
        )

        embed_one = default_embed_one
    embed = embed_one

    class _DeterministicEmbedderPort(EmbedderPort):
        def embed_batch(
            self,
            items: list[Keyed[K, ChunkWithoutEmbedding]],
        ) -> IOPlan[list[Keyed[K, Chunk]]]:
            def thunk() -> Result[list[Keyed[K, Chunk]], ErrInfo]:
                return Ok(
                    [Keyed(key=item.key, value=embed(item.value)) for item in items]
                )

            return io_delay(thunk)

    return _DeterministicEmbedderPort()


__all__ = ["Keyed", "EmbedderPort", "deterministic_embedder_port"]
