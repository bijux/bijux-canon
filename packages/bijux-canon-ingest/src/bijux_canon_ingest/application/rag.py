# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

# mypy: ignore-errors
"""Application services for the RAG ingestion flow.

This module wires:
    clean -> chunk -> index -> retrieve -> (optional rerank) -> generate.

Both CLI and FastAPI boundary call into this layer to avoid drift.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path

import msgpack

from bijux_canon_ingest.core.types import Chunk, RawDoc
from bijux_canon_ingest.retrieval.embedders import HashEmbedder, SentenceTransformersEmbedder
from bijux_canon_ingest.retrieval.generators import ExtractiveGenerator
from bijux_canon_ingest.retrieval.indexes import (
    BM25Index,
    NumpyCosineIndex,
    load_index,
)
from bijux_canon_ingest.retrieval.ports import Answer, Candidate, Embedder
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker
from bijux_canon_ingest.result.types import Err, Ok, Result


def retrieve(
    *,
    index_path: Path,
    query: str,
    top_k: int = 5,
    filters: Mapping[str, str] | None = None,
    embedder: Embedder | None = None,
) -> list[Candidate]:
    """Retrieve candidates from a persisted index."""

    idx = load_index(str(index_path))

    if isinstance(idx, NumpyCosineIndex) and embedder is None:
        # Default embedder based on index spec.
        if idx.spec.model.startswith("sbert:"):
            embedder = SentenceTransformersEmbedder(
                model_name=idx.spec.model.split(":", 1)[1]
            )
        else:
            embedder = HashEmbedder()

    return idx.retrieve(
        query=query, top_k=int(top_k), filters=filters, embedder=embedder
    )


def ask(
    *,
    index_path: Path,
    query: str,
    top_k: int = 5,
    filters: Mapping[str, str] | None = None,
    embedder: Embedder | None = None,
    rerank: bool = True,
) -> Answer:
    """Retrieve and answer with citations."""

    cands = retrieve(
        index_path=index_path,
        query=query,
        top_k=max(20, int(top_k)),
        filters=filters,
        embedder=embedder,
    )
    if rerank:
        cands = LexicalOverlapReranker().rerank(
            query=query, candidates=cands, top_k=int(top_k)
        )
    else:
        cands = cands[: int(top_k)]
    return ExtractiveGenerator().generate(query=query, candidates=cands)


def parse_filters(filters: list[str] | None) -> dict[str, str]:
    """Parse CLI/API filters.

    Args:
        filters: list like ["category=cs.AI", "doc_id=foo"].
    """

    out: dict[str, str] = {}
    for f in filters or []:
        if "=" not in f:
            raise ValueError(f"invalid filter: {f}")
        k, v = f.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k or not v:
            raise ValueError(f"invalid filter: {f}")
        out[k] = v
    return out


__all__ = [
    "IndexBackend",
    "RagIndex",
    "ask",
    "parse_filters",
    "retrieve",
    "RagApp",
]


# ---------------------------
# Modern RagApp facade (index → retrieve → ask)
# ---------------------------


class IndexBackend(StrEnum):
    BM25 = "bm25"
    NUMPY_COSINE = "numpy-cosine"


def _fingerprint_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class RagIndex:
    """In-memory index wrapper for deterministic CI profile."""

    backend: str
    index: BM25Index | NumpyCosineIndex
    fingerprint: str
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class RagApp:
    generator: ExtractiveGenerator = ExtractiveGenerator()
    reranker: LexicalOverlapReranker = LexicalOverlapReranker()
    profile: str = "default"

    # ------------- Build / Save / Load -------------
    def _coerce_raw_doc(self, obj: object) -> RawDoc:
        """Accept RawDoc, mapping, or tuple/list to keep boundaries backward compatible."""

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

    def _raw_docs_to_chunks(
        self, docs: Iterable[object], *, chunk_size: int, overlap: int, tail_policy: str
    ) -> Result[list[Chunk], str]:
        env = RagEnv(chunk_size=chunk_size, overlap=overlap, tail_policy=tail_policy)
        chunks: list[Chunk] = []
        for doc in docs:
            raw = self._coerce_raw_doc(doc)
            cleaned = clean_doc(raw)
            for idx, ch in enumerate(iter_chunk_doc(cleaned, env)):
                created = Chunk.create(
                    doc_id=raw.doc_id,
                    chunk_index=idx,
                    start=ch.start,
                    end=ch.end,
                    text=ch.text,
                    title=raw.title,
                    category=raw.categories,
                    embedding=(),
                    metadata={"title": raw.title, "category": raw.categories},
                )
                if isinstance(created, Err):
                    return Err(created.error)
                chunks.append(created.value)
        return Ok(chunks)

    def build_index(
        self,
        docs: Iterable[RawDoc],
        backend: str = "bm25",
        chunk_size: int = 4096,
        overlap: int = 0,
        tail_policy: str = "emit_short",
    ) -> Result[RagIndex, str]:
        chunk_res = self._raw_docs_to_chunks(
            docs, chunk_size=chunk_size, overlap=overlap, tail_policy=tail_policy
        )
        if isinstance(chunk_res, Err):
            return chunk_res
        chunks = chunk_res.value

        if backend not in ("bm25", "numpy-cosine"):
            return Err(f"unsupported backend: {backend}")

        if backend == "bm25":
            idx = build_bm25_index(chunks=chunks, buckets=2048)
            return Ok(RagIndex(backend="bm25", index=idx, fingerprint=idx.fingerprint))

        emb = HashEmbedder()
        idx = build_numpy_cosine_index(chunks=chunks, embedder=emb)
        return Ok(
            RagIndex(backend="numpy-cosine", index=idx, fingerprint=idx.fingerprint)
        )

    def save_index(self, index: RagIndex, path: Path) -> Result[None, str]:
        try:
            index.index.save(str(path))
            return Ok(None)
        except Exception as exc:  # pragma: no cover
            return Err(str(exc))

    def load_index(self, path: Path) -> Result[RagIndex, str]:
        try:
            idx = load_index(str(path))
            if isinstance(idx, BM25Index):
                return Ok(
                    RagIndex(backend="bm25", index=idx, fingerprint=idx.fingerprint)
                )
            if isinstance(idx, NumpyCosineIndex):
                return Ok(
                    RagIndex(
                        backend="numpy-cosine", index=idx, fingerprint=idx.fingerprint
                    )
                )
            return Err("unknown index backend")
        except Exception as exc:  # pragma: no cover
            return Err(str(exc))

    # ------------- Retrieve / Ask -------------
    def retrieve(
        self,
        index: RagIndex,
        query: str,
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> Result[list[Candidate], str]:
        try:
            embedder = None
            if isinstance(index.index, NumpyCosineIndex):
                spec = index.index.spec
                if isinstance(spec.model, str) and spec.model.startswith("sbert:"):
                    embedder = SentenceTransformersEmbedder(
                        model_name=spec.model.split(":", 1)[1]
                    )
                else:
                    embedder = HashEmbedder()
            fetch_k = max(int(top_k) * 3, 20)
            cands = index.index.retrieve(
                query=query, top_k=fetch_k, filters=filters or {}, embedder=embedder
            )
            # Apply deterministic lexical rerank for CI to stabilise ordering and promote exact matches.
            cands = self.reranker.rerank(query=query, candidates=cands, top_k=top_k)
            return Ok(cands[: max(0, int(top_k))])
        except Exception as exc:  # pragma: no cover
            return Err(str(exc))

    def ask(
        self,
        index: RagIndex,
        query: str,
        top_k: int,
        filters: dict[str, str] | None = None,
        rerank: bool = True,
    ) -> Result[dict[str, object], str]:
        r = self.retrieve(
            index=index,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters or {},
        )
        if isinstance(r, Err):
            return r
        cands = r.value
        if not cands:
            return Err("no candidates retrieved")
        if rerank:
            cands = self.reranker.rerank(query=query, candidates=cands, top_k=top_k)
        else:
            cands = cands[:top_k]

        # Deterministic extractive answer: use top candidate text.
        top = cands[0]
        ans_text = top.chunk.text
        contexts = [
            {
                "doc_id": c.doc_id,
                "text": c.text,
                "start": c.start,
                "end": c.end,
                "chunk_id": c.chunk_id,
                "score": c.score,
            }
            for c in cands[: max(1, top_k)]
        ]
        citations = [
            {
                "doc_id": ctx["doc_id"],
                "chunk_id": ctx["chunk_id"],
                "start": ctx["start"],
                "end": ctx["end"],
                "text": ctx["text"],
            }
            for ctx in contexts
        ]
        return Ok(
            {
                "answer": ans_text,
                "citations": citations,
                "contexts": contexts,
                "candidates": contexts,
            }
        )

    # ------------- Legacy compatibility (blob-based) -------------
    def retrieve_blob(
        self, blob: bytes, query: str, top_k: int, filters: dict[str, str]
    ) -> Result[list[Candidate], str]:
        payload = msgpack.unpackb(blob, raw=False)
        backend = payload.get("backend")
        if backend == "bm25":
            idx = BM25Index.load_bytes(blob)
            return Ok(idx.retrieve(query=query, top_k=top_k, filters=filters))

        if backend == "numpy-cosine":
            idx = NumpyCosineIndex.load_bytes(blob)
            spec = idx.spec
            if isinstance(spec.model, str) and spec.model.startswith("sbert:"):
                emb = SentenceTransformersEmbedder(
                    model_name=spec.model.split(":", 1)[1]
                )
            else:
                emb = HashEmbedder()
            return Ok(
                idx.retrieve(query=query, top_k=top_k, filters=filters, embedder=emb)
            )
        return Err("unknown index backend")

    def ask_blob(
        self,
        blob: bytes,
        query: str,
        top_k: int,
        filters: dict[str, str],
        rerank: bool = True,
    ) -> Result[Answer, str]:
        res = self.retrieve_blob(
            blob=blob,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters,
        )
        if isinstance(res, Err):
            return res
        cands = res.value
        if rerank and cands:
            cands = self.reranker.rerank(query=query, candidates=cands, top_k=top_k)
        else:
            cands = cands[:top_k]
        return Ok(self.generator.generate(query=query, candidates=cands))
