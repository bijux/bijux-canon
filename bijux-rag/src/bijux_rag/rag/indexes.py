# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

# mypy: ignore-errors
"""Reference indexes.

Two backends are provided out of the box:
* NumpyCosineIndex: small/medium corpora, deterministic, dependency-free.
* BM25Index: CI-friendly lexical retrieval without model downloads.

Persistence format: msgpack (schema_versioned).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence

import msgpack
import numpy as np
from numpy.typing import NDArray

from bijux_rag.core.rag_types import Chunk, EmbeddingSpec
from bijux_rag.rag.ports import Candidate, Embedder

SCHEMA_VERSION = 1


def _fingerprint_bytes(*parts: bytes) -> str:
    h = sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()


def _json_dumps(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def _l2_normalize(x: NDArray[np.float32]) -> NDArray[np.float32]:
    denom = np.linalg.norm(x, axis=1, keepdims=True)
    denom = np.maximum(denom, np.float32(1e-12))
    return x / denom


def _stable_token_bucket(token: str, *, buckets: int) -> int:
    # Deterministic across platforms.
    d = sha256(token.encode("utf-8")).digest()
    n = int.from_bytes(d[:8], "big", signed=False)
    return int(n % buckets)


def _tokenize(text: str) -> list[str]:
    # Minimal, deterministic tokenizer.
    # Production: replace with proper tokenization if needed.
    out: list[str] = []
    cur: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


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
        # Deterministic fingerprint. Order by chunk_id to be robust to ingestion order.
        ids = [c.chunk_id for c in self.chunks]
        meta = {
            "schema": SCHEMA_VERSION,
            "backend": self.backend,
            "spec": {
                "model": self.spec.model,
                "dim": self.spec.dim,
                "metric": self.spec.metric,
                "normalized": self.spec.normalized,
            },
            "chunk_ids": ids,
        }
        return _fingerprint_bytes(_json_dumps(meta), self.vectors.tobytes())

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
            raise ValueError(f"embedder model mismatch: {embedder.spec.model} != {self.spec.model}")

        q = embedder.embed_texts([query])
        qv = q[0]
        if self.spec.normalized:
            qv = _l2_normalize(q)[0]
        # vectors are already normalized when built.
        scores = (self.vectors @ qv).astype(np.float32)

        # Apply metadata filters.
        idxs = np.arange(len(self.chunks))
        if filters:
            keep: list[int] = []
            for i in idxs.tolist():
                c = self.chunks[i]
                md = dict(c.metadata)
                ok = True
                for k, v in filters.items():
                    if k == "doc_id" and c.doc_id != v:
                        ok = False
                        break
                    if k not in md:
                        ok = False
                        break
                    if str(md.get(k)) != v:
                        ok = False
                        break
                if ok:
                    keep.append(i)
            idxs = np.asarray(keep, dtype=int)

        if idxs.size == 0:
            return []

        # Partial argpartition for top-k.
        k = min(int(top_k), int(idxs.size))
        sub_scores = scores[idxs]
        top_local = np.argpartition(-sub_scores, kth=k - 1)[:k]
        top_idxs = idxs[top_local]
        top_idxs = top_idxs[np.argsort(-scores[top_idxs])]

        out: list[Candidate] = []
        for i in top_idxs.tolist():
            out.append(
                Candidate(
                    chunk=self.chunks[i], score=float(scores[i]), metadata={"backend": self.backend}
                )
            )
        return out

    def save(self, path: str) -> None:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "backend": self.backend,
            "spec": {
                "model": self.spec.model,
                "dim": self.spec.dim,
                "metric": self.spec.metric,
                "normalized": self.spec.normalized,
            },
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                    "metadata": dict(c.metadata),
                    "chunk_id": c.chunk_id,
                }
                for c in self.chunks
            ],
            "vectors": {
                "dtype": "float32",
                "shape": list(self.vectors.shape),
                "data": self.vectors.tobytes(),
            },
        }
        with open(path, "wb") as f:
            f.write(msgpack.packb(payload, use_bin_type=True))

    def to_bytes(self) -> bytes:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "backend": self.backend,
            "spec": {
                "model": self.spec.model,
                "dim": self.spec.dim,
                "metric": self.spec.metric,
                "normalized": self.spec.normalized,
            },
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                    "metadata": dict(c.metadata),
                    "chunk_id": c.chunk_id,
                }
                for c in self.chunks
            ],
            "vectors": {
                "dtype": "float32",
                "shape": list(self.vectors.shape),
                "data": self.vectors.tobytes(),
            },
        }
        return msgpack.packb(payload, use_bin_type=True)

    @staticmethod
    def load(path: str) -> "NumpyCosineIndex":
        with open(path, "rb") as f:
            payload = msgpack.unpackb(f.read(), raw=False)
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
        chunks_list = []
        for c in payload["chunks"]:
            chk = Chunk(
                doc_id=c["doc_id"],
                text=c["text"],
                start=int(c["start"]),
                end=int(c["end"]),
                metadata=c.get("metadata", {}),
                embedding=(),
                embedding_spec=spec,
            )
            stored_id = c.get("chunk_id")
            if stored_id is not None and chk.chunk_id != stored_id:
                raise ValueError("chunk_id mismatch on load (possible corruption)")
            chunks_list.append(chk)
        chunks = tuple(chunks_list)
        vec = payload["vectors"]
        shape = tuple(int(x) for x in vec["shape"])
        arr = np.frombuffer(vec["data"], dtype=np.float32).reshape(shape)
        return NumpyCosineIndex(chunks=chunks, vectors=arr, spec=spec)

    @classmethod
    def load_bytes(cls, blob: bytes) -> "NumpyCosineIndex":
        payload = msgpack.unpackb(blob, raw=False)
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
        chunks = tuple(
            Chunk(
                doc_id=c["doc_id"],
                text=c["text"],
                start=int(c["start"]),
                end=int(c["end"]),
                metadata=c.get("metadata", {}),
                embedding=(),
                embedding_spec=spec,
            )
            for c in payload["chunks"]
        )
        vec = payload["vectors"]
        shape = tuple(int(x) for x in vec["shape"])
        arr = np.frombuffer(vec["data"], dtype=np.float32).reshape(shape)
        return cls(chunks=chunks, vectors=arr, spec=spec)


@dataclass(frozen=True, slots=True)
class BM25Index:
    """Hashed-token BM25 index.

    This is a practical, CI-friendly retrieval baseline:
    - deterministic
    - no large model downloads
    - supports metadata filters
    """

    chunks: tuple[Chunk, ...]
    buckets: int
    df: NDArray[np.int32]
    tfs: tuple[tuple[tuple[int, int], ...], ...]  # per-chunk sparse (bucket,count)
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
            "chunk_ids": [c.chunk_id for c in self.chunks],
        }
        parts = [_json_dumps(meta), self.df.tobytes(), self.doc_len.tobytes()]
        # Include sparse tf payload deterministically.
        tf_bytes = msgpack.packb(self.tfs, use_bin_type=True)
        parts.append(tf_bytes)
        return _fingerprint_bytes(*parts)

    def _idf(self, bucket: int) -> float:
        n = len(self.chunks)
        df = int(self.df[bucket])
        return math.log((n - df + 0.5) / (df + 0.5) + 1.0)

    def retrieve(
        self,
        *,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        embedder: Embedder | None = None,
    ) -> list[Candidate]:
        # embedder unused; lexical.
        toks = _tokenize(query)
        if not toks:
            return []
        q_counts: dict[int, int] = {}
        for t in toks:
            b = _stable_token_bucket(t, buckets=self.buckets)
            q_counts[b] = q_counts.get(b, 0) + 1

        idxs = range(len(self.chunks))
        if filters:
            filt: list[int] = []
            for i in idxs:
                c = self.chunks[i]
                md = dict(c.metadata)
                ok = True
                for k, v in filters.items():
                    if k == "doc_id" and c.doc_id != v:
                        ok = False
                        break
                    if k not in md:
                        ok = False
                        break
                    if str(md.get(k)) != v:
                        ok = False
                        break
                if ok:
                    filt.append(i)
            idxs = filt

        scores: list[tuple[int, float]] = []
        for i in idxs:
            dl = float(self.doc_len[i])
            denom_norm = self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
            tf_sparse = dict(self.tfs[i])
            s = 0.0
            for bucket, _qtf in q_counts.items():
                tf = float(tf_sparse.get(bucket, 0))
                if tf <= 0.0:
                    continue
                idf = self._idf(bucket)
                s += idf * (tf * (self.k1 + 1.0)) / (tf + denom_norm)
            if s > 0.0:
                scores.append((i, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        out: list[Candidate] = []
        for i, s in scores[: max(0, int(top_k))]:
            out.append(
                Candidate(chunk=self.chunks[i], score=float(s), metadata={"backend": self.backend})
            )
        return out

    def save(self, path: str) -> None:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "backend": self.backend,
            "buckets": self.buckets,
            "k1": self.k1,
            "b": self.b,
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                    "metadata": dict(c.metadata),
                    "chunk_id": c.chunk_id,
                }
                for c in self.chunks
            ],
            "df": self.df.tobytes(),
            "doc_len": self.doc_len.tobytes(),
            "tfs": self.tfs,
            "avg_dl": self.avg_dl,
        }
        with open(path, "wb") as f:
            f.write(msgpack.packb(payload, use_bin_type=True))

    def to_bytes(self) -> bytes:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "backend": self.backend,
            "buckets": self.buckets,
            "k1": self.k1,
            "b": self.b,
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "text": c.text,
                    "start": c.start,
                    "end": c.end,
                    "metadata": dict(c.metadata),
                    "chunk_id": c.chunk_id,
                }
                for c in self.chunks
            ],
            "df": self.df.tobytes(),
            "doc_len": self.doc_len.tobytes(),
            "tfs": self.tfs,
            "avg_dl": self.avg_dl,
        }
        return msgpack.packb(payload, use_bin_type=True)

    @staticmethod
    def load(path: str) -> "BM25Index":
        with open(path, "rb") as f:
            payload = msgpack.unpackb(f.read(), raw=False)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported index schema version")
        if payload.get("backend") != "bm25":
            raise ValueError("not a bm25 index")

        chunks_list = []
        for c in payload["chunks"]:
            chk = Chunk(
                doc_id=c["doc_id"],
                text=c["text"],
                start=int(c["start"]),
                end=int(c["end"]),
                metadata=c.get("metadata", {}),
                embedding=(),
            )
            stored_id = c.get("chunk_id")
            if stored_id is not None and chk.chunk_id != stored_id:
                raise ValueError("chunk_id mismatch on load (possible corruption)")
            chunks_list.append(chk)
        chunks = tuple(chunks_list)
        buckets = int(payload["buckets"])
        n = len(chunks)
        df = np.frombuffer(payload["df"], dtype=np.int32, count=buckets).copy()
        doc_len = np.frombuffer(payload["doc_len"], dtype=np.int32, count=n).copy()
        tfs = tuple(tuple((int(a), int(b)) for a, b in row) for row in payload["tfs"])
        avg_dl = float(payload["avg_dl"])
        return BM25Index(
            chunks=chunks, buckets=buckets, df=df, tfs=tfs, doc_len=doc_len, avg_dl=avg_dl
        )

    @classmethod
    def load_bytes(cls, blob: bytes) -> "BM25Index":
        payload = msgpack.unpackb(blob, raw=False)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported index schema version")
        if payload.get("backend") != "bm25":
            raise ValueError("not a bm25 index")

        chunks = tuple(
            Chunk(
                doc_id=c["doc_id"],
                text=c["text"],
                start=int(c["start"]),
                end=int(c["end"]),
                metadata=c.get("metadata", {}),
                embedding=(),
            )
            for c in payload["chunks"]
        )
        buckets = int(payload["buckets"])
        n = len(chunks)
        df = np.frombuffer(payload["df"], dtype=np.int32, count=buckets).copy()
        doc_len = np.frombuffer(payload["doc_len"], dtype=np.int32, count=n).copy()
        tfs = tuple(tuple((int(a), int(b)) for a, b in row) for row in payload["tfs"])
        avg_dl = float(payload["avg_dl"])
        return cls(chunks=chunks, buckets=buckets, df=df, tfs=tfs, doc_len=doc_len, avg_dl=avg_dl)


def build_numpy_cosine_index(*, chunks: Sequence[Chunk], embedder: Embedder) -> NumpyCosineIndex:
    """Build a dense index from chunk texts."""

    if not chunks:
        raise ValueError("cannot build index from empty chunk list")
    ordered_chunks = sorted(chunks, key=lambda c: c.chunk_id)
    spec = embedder.spec
    texts = [c.text for c in ordered_chunks]
    vecs = embedder.embed_texts(texts)
    if vecs.ndim != 2:
        raise ValueError("embedder must return a 2D array")
    if vecs.shape[0] != len(ordered_chunks):
        raise ValueError("embedder output size mismatch")
    # Spec dim is enforced at the boundary (this is the point of EmbeddingSpec).
    if vecs.shape[1] != spec.dim:
        # Allow embedders to report placeholder dims; in that case, take the real dim.
        spec = EmbeddingSpec(
            model=spec.model, dim=int(vecs.shape[1]), metric=spec.metric, normalized=spec.normalized
        )
    arr = np.asarray(vecs, dtype=np.float32)
    if spec.normalized:
        arr = _l2_normalize(arr)
    out_chunks = tuple(
        Chunk(
            doc_id=c.doc_id,
            text=c.text,
            start=c.start,
            end=c.end,
            metadata=c.metadata,
            embedding=tuple(float(x) for x in arr[i].tolist()),
            embedding_spec=spec,
        )
        for i, c in enumerate(ordered_chunks)
    )
    return NumpyCosineIndex(chunks=out_chunks, vectors=arr, spec=spec)


def build_bm25_index(
    *, chunks: Sequence[Chunk], buckets: int = 2048, k1: float = 1.2, b: float = 0.75
) -> BM25Index:
    """Build a hashed-token BM25 index."""

    if not chunks:
        raise ValueError("cannot build index from empty chunk list")
    n = len(chunks)
    df = np.zeros((buckets,), dtype=np.int32)
    tfs: list[tuple[tuple[int, int], ...]] = []
    doc_len = np.zeros((n,), dtype=np.int32)

    ordered_chunks = sorted(chunks, key=lambda c: c.chunk_id)

    # Compute per-chunk term counts and bucket doc-frequencies.
    for i, c in enumerate(ordered_chunks):
        toks = _tokenize(c.text)
        doc_len[i] = np.int32(len(toks))
        counts: dict[int, int] = {}
        seen: set[int] = set()
        for t in toks:
            bucket = _stable_token_bucket(t, buckets=buckets)
            counts[bucket] = counts.get(bucket, 0) + 1
            seen.add(bucket)
        for bkt in seen:
            df[bkt] += 1
        tfs.append(tuple(sorted(counts.items())))

    avg_dl = float(doc_len.mean()) if n else 0.0
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


def load_index(path: str) -> NumpyCosineIndex | BM25Index:
    """Load an index from disk."""

    with open(path, "rb") as f:
        payload = msgpack.unpackb(f.read(), raw=False)
    backend = payload.get("backend")
    if backend == "bm25":
        return BM25Index.load(path)
    if backend == "numpy-cosine":
        return NumpyCosineIndex.load(path)
    raise ValueError(f"unknown index backend: {backend}")


__all__ = [
    "BM25Index",
    "NumpyCosineIndex",
    "SCHEMA_VERSION",
    "build_bm25_index",
    "build_numpy_cosine_index",
    "load_index",
]
