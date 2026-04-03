# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

# mypy: ignore-errors
"""Application services for the 'real RAG' path.

This module wires:
    clean -> chunk -> index -> retrieve -> (optional rerank) -> generate.

Both CLI and FastAPI boundary call into this layer to avoid drift.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import msgpack

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, RagEnv, RawDoc
from bijux_rag.infra.adapters.file_storage import FileStorage
from bijux_rag.rag.embedders import HashEmbedder, SentenceTransformersEmbedder
from bijux_rag.rag.generators import ExtractiveGenerator
from bijux_rag.rag.indexes import (
    BM25Index,
    NumpyCosineIndex,
    build_bm25_index,
    build_numpy_cosine_index,
    load_index,
)
from bijux_rag.rag.ports import Answer, Candidate, Embedder
from bijux_rag.rag.rerankers import LexicalOverlapReranker
from bijux_rag.rag.stages import (
    clean_doc,
    iter_chunk_doc,
)
from bijux_rag.result.types import Err, Ok, Result, is_err, is_ok


@dataclass(frozen=True, slots=True)
class RagBuildConfig:
    """RAG build configuration."""

    chunk_env: RagEnv
    backend: str = "bm25"
    embedder: str = "hash16"
    sbert_model: str = "all-MiniLM-L6-v2"
    bm25_buckets: int = 2048


def _iter_clean_docs(docs: Iterable[RawDoc]) -> Iterator[CleanDoc]:
    for d in docs:
        yield clean_doc(d)


def _iter_chunks(cleaned: Iterable[CleanDoc], env: RagEnv) -> Iterator[ChunkWithoutEmbedding]:
    for cd in cleaned:
        yield from iter_chunk_doc(cd, env)


def _make_embedder(cfg: RagBuildConfig) -> Embedder:
    if cfg.embedder == "hash16":
        return HashEmbedder()
    if cfg.embedder == "sbert":
        return SentenceTransformersEmbedder(model_name=cfg.sbert_model)
    raise ValueError(f"unknown embedder backend: {cfg.embedder}")


def ingest_csv_to_chunks(*, csv_path: Path, env: RagEnv) -> list[Chunk]:
    """Ingest a CSV and return chunks.

    Args:
        csv_path: CSV path with columns: doc_id,title,abstract,categories.
        env: Chunking configuration.

    Returns:
        A list of chunks (without embeddings for lexical backends).
    """

    storage = FileStorage()
    docs: list[RawDoc] = []
    errors: list[str] = []
    for res in storage.read_docs(str(csv_path)):
        if is_ok(res):
            docs.append(res.value)
        elif is_err(res):
            errors.append(f"{res.error.code}: {res.error.msg}")
        else:  # pragma: no cover
            errors.append("unknown error")

    if errors:
        # Fail fast: ingestion is a boundary operation.
        raise ValueError("CSV parse failures: " + "; ".join(errors[:3]))

    cleaned = list(_iter_clean_docs(docs))
    raw_chunks = list(_iter_chunks(cleaned, env))
    return [
        Chunk(
            doc_id=c.doc_id,
            text=c.text,
            start=c.start,
            end=c.end,
            metadata=c.metadata,
            embedding=(),
        )
        for c in raw_chunks
    ]


def ingest_docs_to_chunks(*, docs: Iterable[RawDoc], env: RagEnv) -> list[Chunk]:
    """Ingest in-memory docs and return chunks."""

    cleaned = list(_iter_clean_docs(docs))
    raw_chunks = list(_iter_chunks(cleaned, env))
    return [
        Chunk(
            doc_id=c.doc_id,
            text=c.text,
            start=c.start,
            end=c.end,
            metadata=c.metadata,
            embedding=(),
        )
        for c in raw_chunks
    ]


def build_index_from_csv(*, csv_path: Path, out_path: Path, cfg: RagBuildConfig) -> str:
    """Build and persist an index.

    Returns:
        The index fingerprint.
    """

    chunks = ingest_csv_to_chunks(csv_path=csv_path, env=cfg.chunk_env)
    if cfg.backend == "bm25":
        idx = build_bm25_index(chunks=chunks, buckets=cfg.bm25_buckets)
        idx.save(str(out_path))
        return idx.fingerprint

    if cfg.backend == "numpy-cosine":
        emb = _make_embedder(cfg)
        idx = build_numpy_cosine_index(chunks=chunks, embedder=emb)
        idx.save(str(out_path))
        return idx.fingerprint

    raise ValueError(f"unknown index backend: {cfg.backend}")


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
            embedder = SentenceTransformersEmbedder(model_name=idx.spec.model.split(":", 1)[1])
        else:
            embedder = HashEmbedder()

    return idx.retrieve(query=query, top_k=int(top_k), filters=filters, embedder=embedder)


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
        cands = LexicalOverlapReranker().rerank(query=query, candidates=cands, top_k=int(top_k))
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
    "RagBuildConfig",
    "RagIndex",
    "ask",
    "build_index_from_csv",
    "ingest_docs_to_chunks",
    "ingest_csv_to_chunks",
    "parse_filters",
    "retrieve",
    "RagApp",
]


# ---------------------------
# Modern RagApp facade (index → retrieve → ask)
# ---------------------------


class IndexBackend(str, Enum):
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
        return Ok(RagIndex(backend="numpy-cosine", index=idx, fingerprint=idx.fingerprint))

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
                return Ok(RagIndex(backend="bm25", index=idx, fingerprint=idx.fingerprint))
            if isinstance(idx, NumpyCosineIndex):
                return Ok(RagIndex(backend="numpy-cosine", index=idx, fingerprint=idx.fingerprint))
            return Err("unknown index backend")
        except Exception as exc:  # pragma: no cover
            return Err(str(exc))

    # ------------- Retrieve / Ask -------------
    def retrieve(
        self, index: RagIndex, query: str, top_k: int, filters: dict[str, str] | None = None
    ) -> Result[list[Candidate], str]:
        try:
            embedder = None
            if isinstance(index.index, NumpyCosineIndex):
                spec = index.index.spec
                if isinstance(spec.model, str) and spec.model.startswith("sbert:"):
                    embedder = SentenceTransformersEmbedder(model_name=spec.model.split(":", 1)[1])
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
                emb = SentenceTransformersEmbedder(model_name=spec.model.split(":", 1)[1])
            else:
                emb = HashEmbedder()
            return Ok(idx.retrieve(query=query, top_k=top_k, filters=filters, embedder=emb))
        return Err("unknown index backend")

    def ask_blob(
        self, blob: bytes, query: str, top_k: int, filters: dict[str, str], rerank: bool = True
    ) -> Result[Answer, str]:
        res = self.retrieve_blob(
            blob=blob, query=query, top_k=max(top_k, 10 if rerank else top_k), filters=filters
        )
        if isinstance(res, Err):
            return res
        cands = res.value
        if rerank and cands:
            cands = self.reranker.rerank(query=query, candidates=cands, top_k=top_k)
        else:
            cands = cands[:top_k]
        return Ok(self.generator.generate(query=query, candidates=cands))
