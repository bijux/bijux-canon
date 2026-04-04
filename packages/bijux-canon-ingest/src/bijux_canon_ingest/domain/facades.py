# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Domain-owned ports for keyed embedding workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from bijux_canon_ingest.core.types import Chunk, ChunkWithoutEmbedding
from bijux_canon_ingest.domain.effects import IOPlan

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
    """Compatibility wrapper for the infrastructure-owned deterministic adapter."""

    from bijux_canon_ingest.infra.adapters.embedder_port import (
        deterministic_embedder_port as build_deterministic_embedder_port,
    )

    return build_deterministic_embedder_port(embed_one=embed_one)


__all__ = ["Keyed", "EmbedderPort", "deterministic_embedder_port"]
