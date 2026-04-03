# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Core domain value types for the Bijux RAG toolkit.

All types are frozen dataclasses → instances are values:
- They support structural equality.
- They are safe to use as dict keys (only `Chunk` opts into `eq=True` for dedup).
- They are safe to share across pure pipeline stages and lazy iterators.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Literal

from bijux_rag.result.types import Err, Ok, Result

TailPolicy = str

# NOTE: keep the core domain model dependency-free.
EmbeddingMetric = Literal["cosine", "dot", "l2"]


@dataclass(frozen=True, slots=True)
class EmbeddingSpec:
    """Embedding configuration attached to an index or a chunk.

    Args:
        model: Identifier for the embedding model/backend.
        dim: Embedding dimensionality.
        metric: Similarity metric used by the index.
        normalized: Whether vectors are L2-normalized before indexing.
    """

    model: str
    dim: int
    metric: EmbeddingMetric = "cosine"
    normalized: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("EmbeddingSpec.model must be a non-empty str")
        if not isinstance(self.dim, int) or self.dim <= 0:
            raise ValueError("EmbeddingSpec.dim must be a positive int")
        if self.metric not in {"cosine", "dot", "l2"}:
            raise ValueError("EmbeddingSpec.metric must be one of: cosine, dot, l2")
        if not isinstance(self.normalized, bool):
            raise ValueError("EmbeddingSpec.normalized must be a bool")

    @classmethod
    def hash16(cls) -> "EmbeddingSpec":
        """Deterministic, dependency-free embedding spec."""

        return cls(model="hash16", dim=16, metric="cosine", normalized=True)

    def validate_embedding(
        self, embedding: tuple[float, ...] | tuple | list | None
    ) -> Result[None, str]:
        """Validate an embedding against this spec."""

        if embedding is None:
            return Ok(None)
        try:
            length = len(embedding)
        except Exception:
            return Err("Embedding must be a sequence")
        if length != self.dim:
            return Err(f"Embedding dim mismatch: expected {self.dim}, got {length}")
        return Ok(None)


def stable_chunk_id(*, doc_id: str, start: int, end: int, text: str) -> str:
    """Compute a deterministic, content-addressed chunk id.

    The id is stable across runs as long as the inputs are stable.

    Args:
        doc_id: Document identifier.
        start: Chunk start offset.
        end: Chunk end offset.
        text: Chunk text.

    Returns:
        A hex digest string.
    """

    payload = f"{doc_id}:{start}:{end}:".encode("utf-8") + text.encode("utf-8")
    return sha256(payload).hexdigest()


@dataclass(frozen=True)
class RawDoc:
    """Raw document as read from the source dataset (CSV row)."""

    doc_id: str
    title: str
    abstract: str
    categories: str


DocRule = Callable[[RawDoc], bool]


@dataclass(frozen=True)
class CleanDoc:
    """Document after deterministic text normalisation."""

    doc_id: str
    title: str
    abstract: str
    categories: str


@dataclass(frozen=True)
class ChunkWithoutEmbedding:
    """A slice of a CleanDoc's abstract before embedding."""

    doc_id: str
    text: str
    start: int
    end: int
    title: str | None = None
    category: str | None = None
    chunk_index: int = 0
    metadata: Mapping[str, object] = field(default_factory=dict, compare=False)
    embedding_spec: EmbeddingSpec | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.start, int) or not isinstance(self.end, int):
            raise ValueError("Chunk offsets must be integers")
        if self.start < 0:
            raise ValueError("Chunk.start must be >= 0")
        if self.end < self.start:
            raise ValueError("Chunk.end must be >= start")
        if not isinstance(self.chunk_index, int) or self.chunk_index < 0:
            raise ValueError("Chunk.chunk_index must be a non-negative int")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("Chunk.metadata must be a mapping")
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def chunk_id(self) -> str:
        """Deterministic id for this chunk."""

        return stable_chunk_id(doc_id=self.doc_id, start=self.start, end=self.end, text=self.text)


@dataclass(frozen=True, eq=True)
class Chunk(ChunkWithoutEmbedding):
    """Final chunk with a deterministic embedding vector."""

    embedding: tuple[float, ...] = ()

    # Optional, non-structural context for enforcing embedding invariants at the index boundary.
    embedding_spec: EmbeddingSpec | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        # NOTE: Do not hard-code dimensionality here. Dim invariants belong to the embedding/index
        # boundary, where an EmbeddingSpec is available.

    @classmethod
    def create(
        cls,
        doc_id: str,
        chunk_index: int,
        start: int,
        end: int,
        text: str,
        title: str | None = None,
        category: str | None = None,
        embedding: Mapping[str, object] | tuple[float, ...] | list[float] | None = None,
        embedding_spec: EmbeddingSpec | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> Result["Chunk", str]:
        """Validated constructor returning Result for boundary code."""

        checks = [
            Ok(None) if chunk_index >= 0 else Err("chunk_index must be non-negative"),
            Ok(None) if start >= 0 else Err("start must be non-negative"),
            Ok(None) if end >= 0 else Err("end must be non-negative"),
            embedding_spec.validate_embedding(tuple(embedding) if embedding is not None else None)
            if embedding_spec is not None
            else Ok(None),
        ]
        for check in checks:
            if isinstance(check, Err):
                return Err(check.error)

        emb_tuple: tuple[float, ...] | tuple = tuple(embedding) if embedding is not None else ()
        return Ok(
            cls(
                doc_id=doc_id,
                title=title,
                category=category,
                chunk_index=chunk_index,
                text=text,
                start=start,
                end=end,
                metadata={} if metadata is None else metadata,
                embedding=emb_tuple,
                embedding_spec=embedding_spec,
            )
        )


@dataclass(frozen=True)
class RagEnv:
    """Immutable configuration for a single pipeline run."""

    chunk_size: int
    sample_size: int = 5
    overlap: int = 0
    tail_policy: TailPolicy = "emit_short"

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_size, int):
            raise ValueError("RagEnv.chunk_size must be an int")
        if self.chunk_size <= 0:
            raise ValueError("RagEnv.chunk_size must be a positive integer")
        if not isinstance(self.sample_size, int):
            raise ValueError("RagEnv.sample_size must be an int")
        if self.sample_size <= 0:
            raise ValueError("RagEnv.sample_size must be a positive integer")
        if not isinstance(self.overlap, int):
            raise ValueError("RagEnv.overlap must be an int")
        if not 0 <= self.overlap < self.chunk_size:
            raise ValueError("RagEnv.overlap must satisfy 0 <= overlap < chunk_size")
        if self.tail_policy not in {"emit_short", "drop", "pad"}:
            raise ValueError('RagEnv.tail_policy must be one of: "emit_short", "drop", "pad"')


@dataclass(frozen=True)
class TextNode:
    """A single text-bearing node in a document hierarchy (Bijux RAG)."""

    text: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, Mapping):
            raise ValueError("TextNode.metadata must be a mapping")
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class TreeDoc:
    """Immutable, recursive document structure (Bijux RAG)."""

    node: TextNode
    children: tuple["TreeDoc", ...] = ()


__all__ = [
    "EmbeddingMetric",
    "EmbeddingSpec",
    "stable_chunk_id",
    "RawDoc",
    "DocRule",
    "CleanDoc",
    "ChunkWithoutEmbedding",
    "Chunk",
    "TailPolicy",
    "RagEnv",
    "TextNode",
    "TreeDoc",
]
