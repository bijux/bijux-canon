# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Pure, composable RAG pipeline stages (end-of-Bijux RAG).

These stages are deterministic and side-effect free. Higher-level APIs wire
them together with configuration-as-data, taps/probes, and boundary adapters.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from bijux_rag.core.rag_types import (
    Chunk,
    ChunkWithoutEmbedding,
    CleanDoc,
    EmbeddingSpec,
    RagEnv,
    RawDoc,
)
from bijux_rag.core.structural_dedup import structural_dedup_lazy
from bijux_rag.result.types import Err, Ok, Result


def clean_doc(doc: RawDoc) -> CleanDoc:
    """Deterministically normalise whitespace and case in the abstract."""

    abstract = " ".join(doc.abstract.strip().lower().split())
    return CleanDoc(
        doc_id=doc.doc_id,
        title=doc.title,
        abstract=abstract,
        categories=doc.categories,
    )


def chunk_doc(doc: CleanDoc, env: RagEnv) -> list[ChunkWithoutEmbedding]:
    """Split a cleaned document into chunks (eager convenience wrapper)."""

    return list(iter_chunk_doc(doc, env))


def iter_overlapping_chunks_text(
    doc_id: str,
    text: str,
    *,
    k: int,
    o: int = 0,
    tail_policy: str = "emit_short",
) -> Iterator[ChunkWithoutEmbedding]:
    """Yield fixed-size chunks from raw text, with optional overlap and tail policy."""

    if k <= 0 or not 0 <= o < k:
        raise ValueError("invalid chunk/overlap")
    if tail_policy not in {"emit_short", "drop", "pad"}:
        raise ValueError('tail_policy must be one of: "emit_short", "drop", "pad"')

    step = k - o
    n = len(text)
    i = 0
    while i < n:
        j = i + k
        short_tail = j > n
        if short_tail and tail_policy == "drop":
            break

        segment = text[i:j]
        if short_tail and tail_policy == "pad":
            segment = segment + "\0" * (k - len(segment))
            j = i + k

        if segment:
            end = j if tail_policy == "pad" else i + len(segment)
            yield ChunkWithoutEmbedding(doc_id=doc_id, text=segment, start=i, end=end)
        i += step


def iter_chunk_spans(doc: CleanDoc, env: RagEnv) -> Iterator[tuple[int, int]]:
    """Yield (start, end) chunk spans for a document."""

    k = env.chunk_size
    o = env.overlap
    tail_policy = env.tail_policy
    if k <= 0 or not 0 <= o < k:
        raise ValueError("invalid chunk/overlap")

    step = k - o
    n = len(doc.abstract)
    i = 0
    while i < n:
        j = i + k
        if j > n and tail_policy == "drop":
            break
        yield (i, j if tail_policy == "pad" else min(j, n))
        i += step


def iter_chunk_doc(doc: CleanDoc, env: RagEnv) -> Iterator[ChunkWithoutEmbedding]:
    """Yield chunks lazily from a cleaned document."""

    yield from iter_overlapping_chunks_text(
        doc_id=doc.doc_id,
        text=doc.abstract,
        k=env.chunk_size,
        o=env.overlap,
        tail_policy=env.tail_policy,
    )


def hash16_embed(text: str) -> tuple[float, ...]:
    """Deterministic placeholder embedder (NOT semantic)."""

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    for i in range(0, 32, 2):
        v = int.from_bytes(digest[i : i + 2], "big")
        out.append(v / 65535.0)
    return tuple(out)


def embed_chunk(chunk: ChunkWithoutEmbedding, *, spec: EmbeddingSpec | None = None) -> Chunk:
    """Produce a deterministic embedding from chunk text."""

    spec = spec or EmbeddingSpec.hash16()
    vector = hash16_embed(chunk.text)
    if spec.dim < len(vector):
        vector = vector[: spec.dim]
    return Chunk(
        doc_id=chunk.doc_id,
        text=chunk.text,
        start=chunk.start,
        end=chunk.end,
        metadata=chunk.metadata,
        embedding=tuple(vector),
        embedding_spec=spec,
    )


def structural_dedup_chunks(chunks: Iterable[Chunk]) -> list[Chunk]:
    """Canonical deduplication: sort by (doc_id, start) then remove duplicates."""

    ordered = sorted(chunks, key=lambda c: (c.doc_id, c.start))
    return list(structural_dedup_lazy(ordered))


@dataclass(frozen=True)
class ChunkConfig:
    chunk_size: int = 512
    overlap: int = 50


@dataclass(frozen=True)
class ChunkAndEmbedConfig(ChunkConfig):
    include_embeddings: bool = True
    embedding_spec: EmbeddingSpec = EmbeddingSpec.hash16()


def chunk_and_embed_docs(
    docs: Iterable[tuple[str, str, str | None, str | None]],
    config: ChunkAndEmbedConfig,
) -> Result[list[Chunk], str]:
    """Utility used by CLI and HTTP adapters."""

    out: list[Chunk] = []
    for doc_id, text, title, category in docs:
        cleaned = " ".join(text.split())
        # chunk with simple sliding window
        idx = 0
        for span in iter_overlapping_chunks_text(
            doc_id=doc_id, text=cleaned, k=config.chunk_size, o=config.overlap
        ):
            chunk_we = ChunkWithoutEmbedding(
                doc_id=doc_id,
                title=title,
                category=category,
                chunk_index=idx,
                text=span.text,
                start=span.start,
                end=span.end,
            )
            if not config.include_embeddings:
                created = Chunk.create(
                    doc_id=chunk_we.doc_id,
                    chunk_index=chunk_we.chunk_index,
                    start=chunk_we.start,
                    end=chunk_we.end,
                    text=chunk_we.text,
                    title=chunk_we.title,
                    category=chunk_we.category,
                    embedding=None,
                    embedding_spec=None,
                )
            else:
                created = Chunk.create(
                    doc_id=chunk_we.doc_id,
                    chunk_index=chunk_we.chunk_index,
                    start=chunk_we.start,
                    end=chunk_we.end,
                    text=chunk_we.text,
                    title=chunk_we.title,
                    category=chunk_we.category,
                    embedding=hash16_embed(chunk_we.text),
                    embedding_spec=config.embedding_spec,
                )
            if isinstance(created, Err):
                return Err(created.error)
            out.append(created.value)
            idx += 1
    return Ok(out)


__all__ = [
    "clean_doc",
    "chunk_doc",
    "iter_chunk_spans",
    "iter_overlapping_chunks_text",
    "iter_chunk_doc",
    "embed_chunk",
    "structural_dedup_chunks",
    "hash16_embed",
    "chunk_and_embed_docs",
    "ChunkAndEmbedConfig",
    "ChunkConfig",
]
