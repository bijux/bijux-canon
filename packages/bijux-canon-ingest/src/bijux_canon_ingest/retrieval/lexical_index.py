# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Lexical BM25 retrieval implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any

import msgpack
import numpy as np
from numpy.typing import NDArray

from bijux_canon_ingest.core.types import Chunk
from bijux_canon_ingest.retrieval._index_common import (
    SCHEMA_VERSION,
    canonical_json_dumps,
    fingerprint_bytes,
)
from bijux_canon_ingest.retrieval.ports import Candidate, Embedder
from bijux_canon_ingest.retrieval.text_analysis import stable_token_bucket, tokenize


@dataclass(frozen=True, slots=True)
class BM25Index:
    """Hashed-token BM25 index."""

    chunks: tuple[Chunk, ...]
    buckets: int
    df: NDArray[np.int32]
    tfs: tuple[tuple[tuple[int, int], ...], ...]
    doc_len: NDArray[np.int32]
    avg_dl: float
    k1: float = 1.2
    b: float = 0.75

    @property
    def backend(self) -> str:
        return "bm25"

    @property
    def fingerprint(self) -> str:
        meta = {
            "schema": SCHEMA_VERSION,
            "backend": self.backend,
            "buckets": self.buckets,
            "k1": self.k1,
            "b": self.b,
            "chunk_ids": [chunk.chunk_id for chunk in self.chunks],
        }
        tf_bytes = msgpack.packb(self.tfs, use_bin_type=True)
        return fingerprint_bytes(
            canonical_json_dumps(meta),
            self.df.tobytes(),
            self.doc_len.tobytes(),
            tf_bytes,
        )

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        embedder: Embedder | None = None,
    ) -> list[Candidate]:
        del embedder
        tokens = tokenize(query)
        if not tokens:
            return []

        query_counts: dict[int, int] = {}
        for token in tokens:
            bucket = stable_token_bucket(token, buckets=self.buckets)
            query_counts[bucket] = query_counts.get(bucket, 0) + 1

        indexes: list[int] = list(range(len(self.chunks)))
        if filters:
            indexes = [
                index
                for index in indexes
                if _chunk_matches_filters(self.chunks[index], filters=filters)
            ]

        scores: list[tuple[int, float]] = []
        for index in indexes:
            doc_length = float(self.doc_len[index])
            denom_norm = self.k1 * (1.0 - self.b + self.b * (doc_length / self.avg_dl))
            sparse_tf = dict(self.tfs[index])
            score = 0.0
            for bucket in query_counts:
                tf = float(sparse_tf.get(bucket, 0))
                if tf <= 0.0:
                    continue
                score += _idf(self, bucket) * (tf * (self.k1 + 1.0)) / (tf + denom_norm)
            if score > 0.0:
                scores.append((index, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        return [
            Candidate(
                chunk=self.chunks[index],
                score=float(score),
                metadata={"backend": self.backend},
            )
            for index, score in scores[: max(0, int(top_k))]
        ]

    def save(self, path: str) -> None:
        with open(path, "wb") as handle:
            handle.write(msgpack.packb(_bm25_payload(self), use_bin_type=True))

    def to_bytes(self) -> bytes:
        return msgpack.packb(_bm25_payload(self), use_bin_type=True)

    @staticmethod
    def load(path: str) -> BM25Index:
        with open(path, "rb") as handle:
            payload = msgpack.unpackb(handle.read(), raw=False)
        return _load_bm25_payload(payload)

    @classmethod
    def load_bytes(cls, blob: bytes) -> BM25Index:
        payload = msgpack.unpackb(blob, raw=False)
        return _load_bm25_payload(payload)


def _idf(index: BM25Index, bucket: int) -> float:
    total_docs = len(index.chunks)
    doc_frequency = int(index.df[bucket])
    return math.log((total_docs - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1.0)


def _chunk_matches_filters(chunk: Chunk, *, filters: Mapping[str, str]) -> bool:
    metadata = dict(chunk.metadata)
    for key, value in filters.items():
        if key == "doc_id" and chunk.doc_id != value:
            return False
        if key not in metadata:
            return False
        if str(metadata.get(key)) != value:
            return False
    return True


def _bm25_payload(index: BM25Index) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "backend": index.backend,
        "buckets": index.buckets,
        "k1": index.k1,
        "b": index.b,
        "chunks": [
            {
                "doc_id": chunk.doc_id,
                "text": chunk.text,
                "start": chunk.start,
                "end": chunk.end,
                "metadata": dict(chunk.metadata),
                "chunk_id": chunk.chunk_id,
            }
            for chunk in index.chunks
        ],
        "df": index.df.tobytes(),
        "doc_len": index.doc_len.tobytes(),
        "tfs": index.tfs,
        "avg_dl": index.avg_dl,
    }


def _load_bm25_payload(payload: dict[str, Any]) -> BM25Index:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported index schema version")
    if payload.get("backend") != "bm25":
        raise ValueError("not a bm25 index")

    chunks: list[Chunk] = []
    for chunk_raw in payload["chunks"]:
        chunk = Chunk(
            doc_id=chunk_raw["doc_id"],
            text=chunk_raw["text"],
            start=int(chunk_raw["start"]),
            end=int(chunk_raw["end"]),
            metadata=chunk_raw.get("metadata", {}),
            embedding=(),
        )
        stored_id = chunk_raw.get("chunk_id")
        if stored_id is not None and chunk.chunk_id != stored_id:
            raise ValueError("chunk_id mismatch on load (possible corruption)")
        chunks.append(chunk)

    bucket_count = int(payload["buckets"])
    chunk_count = len(chunks)
    df = np.frombuffer(payload["df"], dtype=np.int32, count=bucket_count).copy()
    doc_len = np.frombuffer(
        payload["doc_len"], dtype=np.int32, count=chunk_count
    ).copy()
    tfs = tuple(tuple((int(a), int(b)) for a, b in row) for row in payload["tfs"])
    return BM25Index(
        chunks=tuple(chunks),
        buckets=bucket_count,
        df=df,
        tfs=tfs,
        doc_len=doc_len,
        avg_dl=float(payload["avg_dl"]),
        k1=float(payload.get("k1", 1.2)),
        b=float(payload.get("b", 0.75)),
    )


__all__ = ["BM25Index"]
