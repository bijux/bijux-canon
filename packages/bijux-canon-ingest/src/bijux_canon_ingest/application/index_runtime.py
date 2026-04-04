# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared runtime helpers for the in-memory retrieval service."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import msgpack

from bijux_canon_ingest.core.types import Chunk, RagEnv, RawDoc
from bijux_canon_ingest.processing.stages import clean_doc, iter_chunk_doc
from bijux_canon_ingest.retrieval.embedders import (
    HashEmbedder,
    SentenceTransformersEmbedder,
)
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


def coerce_raw_doc(obj: object) -> RawDoc:
    """Accept ``RawDoc``, mapping, or tuple/list to keep boundaries backward compatible."""

    if isinstance(obj, RawDoc):
        return obj
    if isinstance(obj, Mapping):
        return RawDoc(
            doc_id=str(obj.get("doc_id", "")),
            title=str(obj.get("title", "")),
            abstract=str(obj.get("abstract", obj.get("text", ""))),
            categories=str(obj.get("categories", obj.get("category", ""))),
        )
    if isinstance(obj, (list, tuple)):
        doc_id = obj[0] if len(obj) >= 1 else ""
        text = obj[1] if len(obj) >= 2 else ""
        title = obj[2] if len(obj) >= 3 else ""
        category = obj[3] if len(obj) >= 4 else ""
        return RawDoc(
            doc_id=str(doc_id),
            title=str(title or ""),
            abstract=str(text or ""),
            categories=str(category or ""),
        )
    raise TypeError("docs must be RawDoc, mapping, or tuple/list")


def raw_docs_to_chunks(
    docs: Iterable[object],
    *,
    chunk_size: int,
    overlap: int,
    tail_policy: str,
) -> Result[list[Chunk], str]:
    env = RagEnv(chunk_size=chunk_size, overlap=overlap, tail_policy=tail_policy)
    chunks: list[Chunk] = []
    for doc in docs:
        raw = coerce_raw_doc(doc)
        cleaned = clean_doc(raw)
        for index, chunk in enumerate(iter_chunk_doc(cleaned, env)):
            created = Chunk.create(
                doc_id=raw.doc_id,
                chunk_index=index,
                start=chunk.start,
                end=chunk.end,
                text=chunk.text,
                title=raw.title,
                category=raw.categories,
                embedding=(),
                metadata={"title": raw.title, "category": raw.categories},
            )
            if isinstance(created, Err):
                return Err(created.error)
            chunks.append(created.value)
    return Ok(chunks)


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

    cosine_index = build_numpy_cosine_index(chunks=chunks, embedder=HashEmbedder())
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
            embedder = _embedder_for_spec(index.index.spec.model)
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
        embedder = _embedder_for_spec(cosine_index.spec.model)
        return Ok(
            cosine_index.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                embedder=embedder,
            )
        )
    return Err("unknown index backend")


def _embedder_for_spec(model_name: str) -> HashEmbedder | SentenceTransformersEmbedder:
    if isinstance(model_name, str) and model_name.startswith("sbert:"):
        return SentenceTransformersEmbedder(model_name=model_name.split(":", 1)[1])
    return HashEmbedder()


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
    "coerce_raw_doc",
    "load_stored_index",
    "raw_docs_to_chunks",
    "retrieve_blob_candidates",
    "retrieve_candidates",
    "save_stored_index",
]
