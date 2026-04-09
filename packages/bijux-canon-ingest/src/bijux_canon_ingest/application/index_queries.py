# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Query execution helpers for stored retrieval indexes."""

from __future__ import annotations

import msgpack  # type: ignore[import-untyped]

from bijux_canon_ingest.application.index_runtime import IndexBackend, StoredIndex
from bijux_canon_ingest.result.types import Err, Ok, Result
from bijux_canon_ingest.retrieval.embedder_factory import embedder_for_model
from bijux_canon_ingest.retrieval.indexes import BM25Index, NumpyCosineIndex
from bijux_canon_ingest.retrieval.ports import Candidate
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker


def retrieve_candidates(
    *,
    index: StoredIndex,
    query: str,
    top_k: int,
    filters: dict[str, str] | None = None,
    reranker: LexicalOverlapReranker | None = None,
) -> Result[list[Candidate], str]:
    """Retrieve candidates from an in-memory stored index."""

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
    """Retrieve candidates from a serialized index payload."""

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


__all__ = ["retrieve_blob_candidates", "retrieve_candidates"]
