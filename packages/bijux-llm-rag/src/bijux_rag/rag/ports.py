# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""RAG primitives: ports for embedders, indexes, retrieval, and generation.

This module is deliberately dependency-light. Concrete backends live in sibling modules.

The goal is to make bijux-rag *actually* RAG:
ingest -> index -> retrieve (+ optional rerank) -> answer with citations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from bijux_rag.core.rag_types import Chunk, EmbeddingSpec


@dataclass(frozen=True, slots=True)
class Candidate:
    """A retrieved chunk plus score and non-sensitive metadata."""

    chunk: Chunk
    score: float
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False)

    @property
    def doc_id(self) -> str:
        return self.chunk.doc_id

    @property
    def text(self) -> str:
        return self.chunk.text

    @property
    def start(self) -> int:
        return self.chunk.start

    @property
    def end(self) -> int:
        return self.chunk.end

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id


@dataclass(frozen=True, slots=True)
class Citation:
    """A citation referencing an evidence chunk."""

    doc_id: str
    chunk_id: str
    start: int
    end: int
    text: str | None = None


@dataclass(frozen=True, slots=True)
class Answer:
    """A grounded answer.

    Args:
        text: Answer text.
        citations: Evidence citations.
    """

    text: str
    citations: tuple[Citation, ...] = ()
    candidates: tuple[Candidate, ...] = ()


class Embedder(Protocol):
    """Embedder port.

    Implementations must be deterministic given the same inputs and configuration.
    """

    @property
    def spec(self) -> EmbeddingSpec: ...

    def embed_texts(self, texts: Sequence[str]) -> NDArray[np.float32]: ...


class Index(Protocol):
    """Index port.

    Indexes are responsible for persistence (save/load) and schema versioning.
    """

    @property
    def backend(self) -> str: ...

    @property
    def fingerprint(self) -> str: ...

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        embedder: Embedder | None = None,
    ) -> list[Candidate]: ...

    def save(self, path: str) -> None: ...


class Indexer(Protocol):
    """Indexer port."""

    def build(self, *, chunks: Sequence[Chunk], embedder: Embedder | None = None) -> Index: ...


class Reranker(Protocol):
    """Reranker port."""

    def rerank(
        self, *, query: str, candidates: Sequence[Candidate], top_k: int
    ) -> list[Candidate]: ...


class Generator(Protocol):
    """Generator port."""

    def generate(self, *, query: str, candidates: Sequence[Candidate]) -> Answer: ...


__all__ = [
    "Answer",
    "Candidate",
    "Citation",
    "Embedder",
    "Generator",
    "Index",
    "Indexer",
    "Reranker",
]
