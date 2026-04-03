# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Persisted chunk-level BM25 index with provenance fingerprints.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from bijux_rar.core.fingerprints import canonical_dumps, fingerprint_bytes
from bijux_rar.rar.retrieval.bm25 import tokenize
from bijux_rar.rar.retrieval.chunking import Chunk, chunk_document
from bijux_rar.rar.retrieval.corpus import (
    CorpusDoc,
    load_corpus_jsonl_stream,
)

SCHEMA_VERSION = 1


def _sha256_path(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ChunkedBM25Index:
    corpus_sha256: str
    chunk_chars: int
    overlap_chars: int
    max_chunks: int | None
    max_docs: int | None
    chunks: tuple[Chunk, ...]
    doc_tokens: tuple[tuple[str, ...], ...]
    doc_tf: tuple[Counter[str], ...]
    df: Counter[str]
    avgdl: float

    @staticmethod
    def build(
        *,
        docs: Iterable[CorpusDoc],
        corpus_sha256: str,
        chunk_chars: int,
        overlap_chars: int,
        max_chunks: int | None = None,
        max_docs: int | None = None,
    ) -> ChunkedBM25Index:
        all_chunks: list[Chunk] = []
        for doc_seen, d in enumerate(docs, start=1):
            if max_docs is not None and max_docs > 0 and doc_seen > max_docs:
                raise ValueError(f"doc limit exceeded ({max_docs})")
            all_chunks.extend(
                chunk_document(
                    doc_id=d.doc_id,
                    text=d.text,
                    title=d.title,
                    source=d.source,
                    chunk_chars=chunk_chars,
                    overlap_chars=overlap_chars,
                )
            )
            if max_chunks is not None and len(all_chunks) > max_chunks:
                raise ValueError(f"chunk limit exceeded ({max_chunks})")
        # Ensure deterministic ordering irrespective of input platform
        all_chunks.sort(key=lambda c: (c.doc_id, c.start_byte, c.end_byte, c.chunk_id))
        if not all_chunks:
            raise ValueError("Cannot build index for empty corpus")

        toks: list[tuple[str, ...]] = []
        tfs: list[Counter[str]] = []
        df: Counter[str] = Counter()
        total_len = 0
        for ch in all_chunks:
            tt = tuple(tokenize(ch.text))
            toks.append(tt)
            tf = Counter(tt)
            tfs.append(tf)
            total_len += len(tt)
            for term in tf:
                df[term] += 1
        avgdl = total_len / float(len(all_chunks))
        return ChunkedBM25Index(
            corpus_sha256=corpus_sha256,
            chunk_chars=int(chunk_chars),
            overlap_chars=int(overlap_chars),
            max_chunks=max_chunks,
            max_docs=max_docs,
            chunks=tuple(all_chunks),
            doc_tokens=tuple(toks),
            doc_tf=tuple(tfs),
            df=df,
            avgdl=avgdl,
        )

    def score(
        self,
        query_tokens: list[str],
        *,
        k1: float = 1.2,
        b: float = 0.75,
        parallel: bool = False,
    ) -> list[float]:
        import math

        doc_count = len(self.chunks)
        scores = [0.0 for _ in range(doc_count)]
        q_terms = Counter(query_tokens)

        def _score_one(i: int) -> tuple[int, float]:
            dl = len(self.doc_tokens[i])
            tf = self.doc_tf[i]
            denom_norm = k1 * (1.0 - b + b * (dl / self.avgdl))
            s = 0.0
            for term, qf in q_terms.items():
                n = self.df.get(term, 0)
                if n == 0:
                    continue
                idf = math.log(1.0 + (doc_count - n + 0.5) / (n + 0.5))
                f = tf.get(term, 0)
                if f == 0:
                    continue
                s += idf * ((f * (k1 + 1.0)) / (f + denom_norm)) * float(qf)
            return i, round(s, 6)

        if parallel and doc_count > 1:
            with ThreadPoolExecutor() as ex:
                for idx, val in ex.map(_score_one, range(doc_count)):
                    scores[idx] = val
        else:
            for i in range(doc_count):
                _, val = _score_one(i)
                scores[i] = val
        return scores

    def top_k(
        self,
        query: str,
        *,
        k: int = 3,
        k1: float = 1.2,
        b: float = 0.75,
        parallel: bool = False,
    ) -> list[tuple[Chunk, float]]:
        qt = tokenize(query)
        scores = self.score(qt, k1=k1, b=b, parallel=parallel)
        ranked = sorted(
            ((self.chunks[i], scores[i]) for i in range(len(self.chunks))),
            key=lambda x: (-round(x[1], 6), x[0].doc_id, x[0].chunk_id),
        )
        return ranked[: max(0, int(k))]

    def to_json(self) -> bytes:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "corpus_sha256": self.corpus_sha256,
            "chunk_chars": self.chunk_chars,
            "overlap_chars": self.overlap_chars,
            "max_chunks": self.max_chunks,
            "max_docs": self.max_docs,
            "avgdl": self.avgdl,
            "df": dict(sorted(self.df.items())),
            "chunks": [
                {
                    "doc_id": c.doc_id,
                    "doc_sha256": c.doc_sha256,
                    "chunk_id": c.chunk_id,
                    "start_byte": c.start_byte,
                    "end_byte": c.end_byte,
                    "text": c.text,
                    "title": c.title,
                    "source": c.source,
                }
                for c in self.chunks
            ],
            "doc_tf": [dict(sorted(tf.items())) for tf in self.doc_tf],
        }
        return canonical_dumps(payload).encode("utf-8")

    @staticmethod
    def from_json(data: bytes) -> ChunkedBM25Index:
        obj = json.loads(data.decode("utf-8"))
        if int(obj.get("schema_version", 0)) != SCHEMA_VERSION:
            raise ValueError("Unsupported chunked BM25 schema_version")
        corpus_sha = str(obj["corpus_sha256"])
        chunk_chars = int(obj["chunk_chars"])
        overlap_chars = int(obj["overlap_chars"])
        max_chunks = obj.get("max_chunks")
        if max_chunks is not None:
            max_chunks = int(max_chunks)
        max_docs = obj.get("max_docs")
        if max_docs is not None:
            max_docs = int(max_docs)
        avgdl = float(obj["avgdl"])
        df = Counter({str(k): int(v) for k, v in dict(obj["df"]).items()})
        raw_chunks = obj["chunks"]
        raw_tf = obj["doc_tf"]
        if len(raw_chunks) != len(raw_tf):
            raise ValueError("Index corruption: mismatched chunk/tf lengths")

        chunks: list[Chunk] = []
        doc_tokens: list[tuple[str, ...]] = []
        doc_tf: list[Counter[str]] = []
        for ch_obj, tf_obj in zip(raw_chunks, raw_tf, strict=True):
            ch = Chunk(
                doc_id=str(ch_obj["doc_id"]),
                doc_sha256=str(ch_obj["doc_sha256"]),
                chunk_id=str(ch_obj["chunk_id"]),
                start_byte=int(ch_obj["start_byte"]),
                end_byte=int(ch_obj["end_byte"]),
                text=str(ch_obj["text"]),
                title=ch_obj.get("title")
                if isinstance(ch_obj.get("title"), str)
                else None,
                source=ch_obj.get("source")
                if isinstance(ch_obj.get("source"), str)
                else None,
            )
            chunks.append(ch)
            tf = Counter({str(k): int(v) for k, v in dict(tf_obj).items()})
            doc_tf.append(tf)
            doc_tokens.append(tuple(tokenize(ch.text)))

        return ChunkedBM25Index(
            corpus_sha256=corpus_sha,
            chunk_chars=chunk_chars,
            overlap_chars=overlap_chars,
            max_chunks=max_chunks,
            max_docs=max_docs,
            chunks=tuple(chunks),
            doc_tokens=tuple(doc_tokens),
            doc_tf=tuple(doc_tf),
            df=df,
            avgdl=avgdl,
        )


def build_or_load_index(
    *,
    corpus_path: Path,
    index_path: Path | None,
    chunk_chars: int,
    overlap_chars: int,
    corpus_max_bytes: int | None = None,
    max_docs: int | None = None,
    max_chunks: int | None = None,
    **_: object,
) -> tuple[ChunkedBM25Index, str, str]:
    """Build or load a persisted index. Returns (index, corpus_sha, index_sha)."""
    corpus_sha = _sha256_path(corpus_path)
    if index_path is not None and index_path.exists():
        raw = index_path.read_bytes()
        try:
            idx = ChunkedBM25Index.from_json(raw)
        except Exception:  # noqa: BLE001
            idx = None
        if idx is not None and (
            idx.corpus_sha256 == corpus_sha
            and idx.chunk_chars == int(chunk_chars)
            and idx.overlap_chars == int(overlap_chars)
            and idx.max_chunks == max_chunks
            and idx.max_docs == max_docs
        ):
            return idx, corpus_sha, _sha256_path(index_path)

    docs = load_corpus_jsonl_stream(
        corpus_path, max_bytes=corpus_max_bytes, max_docs=max_docs
    )
    idx = ChunkedBM25Index.build(
        docs=docs,
        corpus_sha256=corpus_sha,
        chunk_chars=chunk_chars,
        overlap_chars=overlap_chars,
        max_chunks=max_chunks,
        max_docs=max_docs,
    )
    raw = idx.to_json()
    if index_path is not None:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_bytes(raw)
    return idx, corpus_sha, fingerprint_bytes(raw)
