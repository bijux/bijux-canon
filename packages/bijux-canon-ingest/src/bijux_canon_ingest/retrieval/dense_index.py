# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Dense vector retrieval implementation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import msgpack  # type: ignore[import-untyped]
import numpy as np
from numpy.typing import NDArray

from bijux_canon_ingest.core.types import Chunk, EmbeddingSpec
from bijux_canon_ingest.retrieval._index_common import (
    SCHEMA_VERSION,
    canonical_json_dumps,
    fingerprint_bytes,
    l2_normalize,
)
from bijux_canon_ingest.retrieval.ports import Candidate, Embedder


@dataclass(frozen=True, slots=True)
class NumpyCosineIndex:
    """Dense vector index using cosine similarity."""

    chunks: tuple[Chunk, ...]
    vectors: NDArray[np.float32]
    spec: EmbeddingSpec

    @property
    def backend(self) -> str:
        return "numpy-cosine"

    @property
    def fingerprint(self) -> str:
        meta = {
            "schema": SCHEMA_VERSION,
            "backend": self.backend,
            "spec": {
                "model": self.spec.model,
                "dim": self.spec.dim,
                "metric": self.spec.metric,
                "normalized": self.spec.normalized,
            },
            "chunk_ids": [chunk.chunk_id for chunk in self.chunks],
        }
        return fingerprint_bytes(canonical_json_dumps(meta), self.vectors.tobytes())

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        embedder: Embedder | None = None,
    ) -> list[Candidate]:
        if embedder is None:
            raise ValueError("embedder is required for dense retrieval")
        if embedder.spec.model != self.spec.model:
            raise ValueError(
                f"embedder model mismatch: {embedder.spec.model} != {self.spec.model}"
            )

        query_vectors = embedder.embed_texts([query])
        query_vector = query_vectors[0]
        if self.spec.normalized:
            query_vector = l2_normalize(query_vectors)[0]
        scores = (self.vectors @ query_vector).astype(np.float32)

        indexes = np.arange(len(self.chunks))
        if filters:
            kept: list[int] = []
            for index in indexes.tolist():
                chunk = self.chunks[index]
                metadata = dict(chunk.metadata)
                if _chunk_matches_filters(
                    chunk=chunk, metadata=metadata, filters=filters
                ):
                    kept.append(index)
            indexes = np.asarray(kept, dtype=int)

        if indexes.size == 0:
            return []

        limited_top_k = min(int(top_k), int(indexes.size))
        subset_scores = scores[indexes]
        top_local = np.argpartition(-subset_scores, kth=limited_top_k - 1)[
            :limited_top_k
        ]
        top_indexes = indexes[top_local]
        top_indexes = top_indexes[np.argsort(-scores[top_indexes])]

        return [
            Candidate(
                chunk=self.chunks[index],
                score=float(scores[index]),
                metadata={"backend": self.backend},
            )
            for index in top_indexes.tolist()
        ]

    def save(self, path: str) -> None:
        with open(path, "wb") as handle:
            handle.write(msgpack.packb(_dense_payload(self), use_bin_type=True))

    def to_bytes(self) -> bytes:
        return msgpack.packb(_dense_payload(self), use_bin_type=True)

    @staticmethod
    def load(path: str) -> NumpyCosineIndex:
        with open(path, "rb") as handle:
            payload = msgpack.unpackb(handle.read(), raw=False)
        return _load_dense_payload(payload)

    @classmethod
    def load_bytes(cls, blob: bytes) -> NumpyCosineIndex:
        payload = msgpack.unpackb(blob, raw=False)
        return _load_dense_payload(payload)


def _chunk_matches_filters(
    *,
    chunk: Chunk,
    metadata: dict[str, object],
    filters: Mapping[str, str],
) -> bool:
    for key, value in filters.items():
        if key == "doc_id" and chunk.doc_id != value:
            return False
        if key not in metadata:
            return False
        if str(metadata.get(key)) != value:
            return False
    return True


def _dense_payload(index: NumpyCosineIndex) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "backend": index.backend,
        "spec": {
            "model": index.spec.model,
            "dim": index.spec.dim,
            "metric": index.spec.metric,
            "normalized": index.spec.normalized,
        },
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
        "vectors": {
            "dtype": "float32",
            "shape": list(index.vectors.shape),
            "data": index.vectors.tobytes(),
        },
    }


def _load_dense_payload(payload: dict[str, Any]) -> NumpyCosineIndex:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported index schema version")
    if payload.get("backend") != "numpy-cosine":
        raise ValueError("not a numpy-cosine index")

    spec_raw = payload["spec"]
    spec = EmbeddingSpec(
        model=spec_raw["model"],
        dim=int(spec_raw["dim"]),
        metric=spec_raw.get("metric", "cosine"),
        normalized=bool(spec_raw.get("normalized", True)),
    )
    chunks: list[Chunk] = []
    for chunk_raw in payload["chunks"]:
        chunk = Chunk(
            doc_id=chunk_raw["doc_id"],
            text=chunk_raw["text"],
            start=int(chunk_raw["start"]),
            end=int(chunk_raw["end"]),
            metadata=chunk_raw.get("metadata", {}),
            embedding=(),
            embedding_spec=spec,
        )
        stored_id = chunk_raw.get("chunk_id")
        if stored_id is not None and chunk.chunk_id != stored_id:
            raise ValueError("chunk_id mismatch on load (possible corruption)")
        chunks.append(chunk)

    vector_payload = payload["vectors"]
    shape = tuple(int(value) for value in vector_payload["shape"])
    vectors = np.frombuffer(vector_payload["data"], dtype=np.float32).reshape(shape)
    return NumpyCosineIndex(chunks=tuple(chunks), vectors=vectors, spec=spec)


__all__ = ["NumpyCosineIndex"]
