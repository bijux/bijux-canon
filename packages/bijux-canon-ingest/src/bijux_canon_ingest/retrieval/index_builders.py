# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Factories for retrieval indexes."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from bijux_canon_ingest.core.types import Chunk, EmbeddingSpec
from bijux_canon_ingest.retrieval._index_common import l2_normalize
from bijux_canon_ingest.retrieval.dense_index import NumpyCosineIndex
from bijux_canon_ingest.retrieval.index_loading import load_index
from bijux_canon_ingest.retrieval.lexical_index import BM25Index
from bijux_canon_ingest.retrieval.ports import Embedder
from bijux_canon_ingest.retrieval.text_analysis import stable_token_bucket, tokenize


def build_numpy_cosine_index(
    *,
    chunks: Sequence[Chunk],
    embedder: Embedder,
) -> NumpyCosineIndex:
    """Build a dense index from chunk texts."""

    if not chunks:
        raise ValueError("cannot build index from empty chunk list")

    ordered_chunks = sorted(chunks, key=lambda chunk: chunk.chunk_id)
    spec = embedder.spec
    vectors = embedder.embed_texts([chunk.text for chunk in ordered_chunks])
    if vectors.ndim != 2:
        raise ValueError("embedder must return a 2D array")
    if vectors.shape[0] != len(ordered_chunks):
        raise ValueError("embedder output size mismatch")
    if vectors.shape[1] != spec.dim:
        spec = EmbeddingSpec(
            model=spec.model,
            dim=int(vectors.shape[1]),
            metric=spec.metric,
            normalized=spec.normalized,
        )

    array = np.asarray(vectors, dtype=np.float32)
    if spec.normalized:
        array = l2_normalize(array)
    out_chunks = tuple(
        Chunk(
            doc_id=chunk.doc_id,
            text=chunk.text,
            start=chunk.start,
            end=chunk.end,
            metadata=chunk.metadata,
            embedding=tuple(float(value) for value in array[index].tolist()),
            embedding_spec=spec,
        )
        for index, chunk in enumerate(ordered_chunks)
    )
    return NumpyCosineIndex(chunks=out_chunks, vectors=array, spec=spec)


def build_bm25_index(
    *,
    chunks: Sequence[Chunk],
    buckets: int = 2048,
    k1: float = 1.2,
    b: float = 0.75,
) -> BM25Index:
    """Build a hashed-token BM25 index."""

    if not chunks:
        raise ValueError("cannot build index from empty chunk list")

    ordered_chunks = sorted(chunks, key=lambda chunk: chunk.chunk_id)
    chunk_count = len(ordered_chunks)
    df = np.zeros((buckets,), dtype=np.int32)
    tfs: list[tuple[tuple[int, int], ...]] = []
    doc_len = np.zeros((chunk_count,), dtype=np.int32)

    for index, chunk in enumerate(ordered_chunks):
        tokens = tokenize(chunk.text)
        doc_len[index] = np.int32(len(tokens))
        counts: dict[int, int] = {}
        seen: set[int] = set()
        for token in tokens:
            bucket = stable_token_bucket(token, buckets=buckets)
            counts[bucket] = counts.get(bucket, 0) + 1
            seen.add(bucket)
        for bucket in seen:
            df[bucket] += 1
        tfs.append(tuple(sorted(counts.items())))

    avg_dl = float(doc_len.mean()) if chunk_count else 0.0
    return BM25Index(
        chunks=tuple(ordered_chunks),
        buckets=buckets,
        df=df,
        tfs=tuple(tfs),
        doc_len=doc_len,
        avg_dl=avg_dl,
        k1=float(k1),
        b=float(b),
    )
__all__ = ["build_bm25_index", "build_numpy_cosine_index", "load_index"]
