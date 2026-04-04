# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Infrastructure implementations for embedding ports."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from bijux_canon_ingest.core.types import Chunk, ChunkWithoutEmbedding
from bijux_canon_ingest.domain.facades import EmbedderPort, Keyed
from bijux_canon_ingest.domain.effects import IOPlan, io_delay
from bijux_canon_ingest.processing.stages import embed_chunk
from bijux_canon_ingest.result.types import ErrInfo, Ok, Result

K = TypeVar("K")


def deterministic_embedder_port(
    *,
    embed_one: Callable[[ChunkWithoutEmbedding], Chunk] | None = None,
) -> EmbedderPort:
    """Return an adapter that delays deterministic embedding behind ``IOPlan``."""

    embed = embed_one or embed_chunk

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


__all__ = ["deterministic_embedder_port"]
