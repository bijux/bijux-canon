# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Index construction helpers for the in-memory retrieval service."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_ingest.application.document_inputs import raw_docs_to_chunks
from bijux_canon_ingest.retrieval.embedder_factory import embedder_for_model
from bijux_canon_ingest.retrieval.indexes import (
    BM25Index,
    NumpyCosineIndex,
    build_bm25_index,
    build_numpy_cosine_index,
)
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
__all__ = [
    "IndexBackend",
    "StoredIndex",
    "build_stored_index",
]
