# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG hybrid performance path: optimized batches with equivalence checks (end-of-Bijux RAG; domain-modeling)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Literal, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from bijux_rag.fp.error import ErrInfo
from bijux_rag.fp.validation import Validation, VSuccess, v_success

from .chunk import Chunk, assemble
from .embedding import Embedding
from .metadata import ChunkMetadata
from .text import ChunkText

__all__ = [
    "OBatch",
    "to_optimized_batch",
    "from_optimized_batch",
    "process_batch_hybrid",
]


def _embed_one(text: str, *, dim: int = 16) -> tuple[float, ...]:
    h = sha256(text.encode("utf-8")).digest()
    step = len(h) // dim
    if step < 1:
        raise ValueError("dim too large for embedding hash")
    out: list[float] = []
    for i in range(dim):
        chunk = h[i * step : (i + 1) * step]
        n = int.from_bytes(chunk, "big")
        denom = float(2 ** (8 * len(chunk)) - 1)
        out.append(float(np.float32(n / denom)))
    return tuple(out)


def embed_many(texts: Sequence[str], *, dim: int = 16) -> NDArray[np.float32]:
    return np.asarray([_embed_one(t, dim=dim) for t in texts], dtype=np.float32)


def pure_embed(chunk: Chunk) -> Validation[Chunk, ErrInfo]:
    model = chunk.metadata.embedding_model or "unknown"
    emb = Embedding(vector=_embed_one(chunk.text.content), model=model)
    v = assemble(chunk.text, chunk.metadata, emb)
    if isinstance(v, VSuccess):
        return v_success(replace(v.value, id=chunk.id))
    return v


@dataclass(slots=True)
class OBatch:
    rows: list["OChunk"]
    embeddings: NDArray[np.float32] | None = None


@dataclass(slots=True)
class OChunk:
    id: UUID
    text: str
    source: str
    tags: list[str]
    model: str | None
    expected_dim: int | None
    row: int | None = None


def to_optimized_batch(chunks: Sequence[Chunk]) -> OBatch:
    rows: list[OChunk] = []
    for chunk in chunks:
        rows.append(
            OChunk(
                id=chunk.id,
                text=chunk.text.content,
                source=chunk.metadata.source,
                tags=list(chunk.metadata.tags),
                model=chunk.metadata.embedding_model,
                expected_dim=chunk.metadata.expected_dim,
            )
        )
    return OBatch(rows=rows, embeddings=None)


def from_optimized_batch(ob: OBatch) -> list[Validation[Chunk, ErrInfo]]:
    out: list[Validation[Chunk, ErrInfo]] = []
    for i, oc in enumerate(ob.rows):
        text = ChunkText(content=oc.text)
        meta = ChunkMetadata(
            source=oc.source,
            tags=tuple(oc.tags),
            embedding_model=oc.model,
            expected_dim=oc.expected_dim,
        )
        emb = None
        if ob.embeddings is not None:
            vec = tuple(float(x) for x in ob.embeddings[i].tolist())
            model = oc.model or "unknown"
            emb = Embedding(vector=vec, model=model)
        v = assemble(text, meta, emb)
        if isinstance(v, VSuccess):
            out.append(v_success(replace(v.value, id=oc.id)))
        else:
            out.append(v)
    return out


def process_batch_hybrid(
    batch: list[Chunk],
    *,
    mode: Literal["pure", "hybrid"] = "hybrid",
) -> list[Validation[Chunk, ErrInfo]]:
    if mode == "pure":
        return [pure_embed(c) for c in batch]

    ob = to_optimized_batch(batch)
    texts = [r.text for r in ob.rows]
    ob.embeddings = embed_many(texts)
    return from_optimized_batch(ob)
