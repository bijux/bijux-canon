# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared runtime helpers for the in-memory retrieval service."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import msgpack

from bijux_canon_ingest.application.document_inputs import raw_docs_to_chunks
from bijux_canon_ingest.retrieval.embedder_factory import embedder_for_model
from bijux_canon_ingest.retrieval.indexes import (
    BM25Index,
    NumpyCosineIndex,
    build_bm25_index,
    build_numpy_cosine_index,
    load_index,
)
from bijux_canon_ingest.retrieval.ports import Candidate
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker
from bijux_canon_ingest.result.types import Err, Ok, Result


class IndexBackend(StrEnum):
    BM25 = "bm25"
    NUMPY_COSINE = "numpy-cosine"


@dataclass(frozen=True, slots=True)
class StoredIndex:
    """In-memory index wrapper for deterministic CI profile."""

    backend: str
    index: BM25Index | NumpyCosineIndex
    fingerprint: str
    schema_version: int = 1


def build_stored_index(
    *,
    docs: Iterable[object],
    backend: str,
    chunk_size: int,
    overlap: int,
    tail_policy: str,
) -> Result[StoredIndex, str]:
    chunk_result = raw_docs_to_chunks(
        docs,
        chunk_size=chunk_size,
        overlap=overlap,
        tail_policy=tail_policy,
    )
    if isinstance(chunk_result, Err):
        return Err(chunk_result.error)

    chunks = chunk_result.value
    if backend not in (IndexBackend.BM25, IndexBackend.NUMPY_COSINE):
        return Err(f"unsupported backend: {backend}")
    if backend == IndexBackend.BM25:
        bm25_index = build_bm25_index(chunks=chunks, buckets=2048)
        return Ok(
            StoredIndex(
                backend=IndexBackend.BM25,
                index=bm25_index,
                fingerprint=bm25_index.fingerprint,
            )
        )

    cosine_index = build_numpy_cosine_index(
        chunks=chunks,
        embedder=embedder_for_model("hash16"),
    )
    return Ok(
        StoredIndex(
            backend=IndexBackend.NUMPY_COSINE,
            index=cosine_index,
            fingerprint=cosine_index.fingerprint,
        )
    )


def save_stored_index(index: StoredIndex, path: Path) -> Result[None, str]:
    try:
        index.index.save(str(path))
        return Ok(None)
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def load_stored_index(path: Path) -> Result[StoredIndex, str]:
    try:
        index = load_index(str(path))
        return Ok(_wrap_loaded_index(index))
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def retrieve_candidates(
    *,
    index: StoredIndex,
    query: str,
    top_k: int,
    filters: dict[str, str] | None = None,
    reranker: LexicalOverlapReranker | None = None,
) -> Result[list[Candidate], str]:
    try:
        embedder = None
        if isinstance(index.index, NumpyCosineIndex):
            embedder = embedder_for_model(index.index.spec.model)
        fetch_k = max(int(top_k) * 3, 20)
        candidates = index.index.retrieve(
            query=query,
            top_k=fetch_k,
            filters=filters or {},
            embedder=embedder,
        )
        if reranker is not None:
            candidates = reranker.rerank(
                query=query, candidates=candidates, top_k=top_k
            )
        return Ok(candidates[: max(0, int(top_k))])
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def retrieve_blob_candidates(
    *,
    blob: bytes,
    query: str,
    top_k: int,
    filters: dict[str, str],
) -> Result[list[Candidate], str]:
    payload = msgpack.unpackb(blob, raw=False)
    backend = payload.get("backend")
    if backend == IndexBackend.BM25:
        bm25_index = BM25Index.load_bytes(blob)
        return Ok(bm25_index.retrieve(query=query, top_k=top_k, filters=filters))
    if backend == IndexBackend.NUMPY_COSINE:
        cosine_index = NumpyCosineIndex.load_bytes(blob)
        embedder = embedder_for_model(cosine_index.spec.model)
        return Ok(
            cosine_index.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                embedder=embedder,
            )
        )
    return Err("unknown index backend")


def _wrap_loaded_index(index: BM25Index | NumpyCosineIndex) -> StoredIndex:
    if isinstance(index, BM25Index):
        return StoredIndex(
            backend=IndexBackend.BM25,
            index=index,
            fingerprint=index.fingerprint,
        )
    if isinstance(index, NumpyCosineIndex):
        return StoredIndex(
            backend=IndexBackend.NUMPY_COSINE,
            index=index,
            fingerprint=index.fingerprint,
        )
    raise ValueError("unknown index backend")


__all__ = [
    "IndexBackend",
    "StoredIndex",
    "build_stored_index",
    "load_stored_index",
    "retrieve_blob_candidates",
    "retrieve_candidates",
    "save_stored_index",
]
