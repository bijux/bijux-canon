# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Index-building workflows for the ingest package."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from bijux_canon_ingest.core.types import Chunk, ChunkWithoutEmbedding, CleanDoc, RagEnv, RawDoc
from bijux_canon_ingest.infra.adapters.file_storage import FileStorage
from bijux_canon_ingest.processing.stages import clean_doc, iter_chunk_doc
from bijux_canon_ingest.result.types import is_err, is_ok
from bijux_canon_ingest.retrieval.embedders import HashEmbedder, SentenceTransformersEmbedder
from bijux_canon_ingest.retrieval.indexes import build_bm25_index, build_numpy_cosine_index
from bijux_canon_ingest.retrieval.ports import Embedder


@dataclass(frozen=True, slots=True)
class IndexBuildConfig:
    """Settings for building a persisted retrieval index from source documents."""

    chunk_env: RagEnv
    backend: str = "bm25"
    embedder: str = "hash16"
    sbert_model: str = "all-MiniLM-L6-v2"
    bm25_buckets: int = 2048


def _iter_clean_docs(docs: Iterable[RawDoc]) -> Iterator[CleanDoc]:
    for doc in docs:
        yield clean_doc(doc)


def _iter_chunks(
    cleaned: Iterable[CleanDoc], env: RagEnv
) -> Iterator[ChunkWithoutEmbedding]:
    for clean_doc_item in cleaned:
        yield from iter_chunk_doc(clean_doc_item, env)


def _make_embedder(cfg: IndexBuildConfig) -> Embedder:
    if cfg.embedder == "hash16":
        return HashEmbedder()
    if cfg.embedder == "sbert":
        return SentenceTransformersEmbedder(model_name=cfg.sbert_model)
    raise ValueError(f"unknown embedder backend: {cfg.embedder}")


def ingest_csv_to_chunks(*, csv_path: Path, env: RagEnv) -> list[Chunk]:
    """Read a CSV corpus and return chunk records ready for indexing."""

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
        raise ValueError("CSV parse failures: " + "; ".join(errors[:3]))

    cleaned = list(_iter_clean_docs(docs))
    raw_chunks = list(_iter_chunks(cleaned, env))
    return [
        Chunk(
            doc_id=chunk.doc_id,
            text=chunk.text,
            start=chunk.start,
            end=chunk.end,
            metadata=chunk.metadata,
            embedding=(),
        )
        for chunk in raw_chunks
    ]


def ingest_docs_to_chunks(*, docs: Iterable[RawDoc], env: RagEnv) -> list[Chunk]:
    """Chunk in-memory documents without touching the persistence layer."""

    cleaned = list(_iter_clean_docs(docs))
    raw_chunks = list(_iter_chunks(cleaned, env))
    return [
        Chunk(
            doc_id=chunk.doc_id,
            text=chunk.text,
            start=chunk.start,
            end=chunk.end,
            metadata=chunk.metadata,
            embedding=(),
        )
        for chunk in raw_chunks
    ]


def build_index_from_csv(
    *, csv_path: Path, out_path: Path, cfg: IndexBuildConfig
) -> str:
    """Build and persist a retrieval index from a CSV corpus."""

    chunks = ingest_csv_to_chunks(csv_path=csv_path, env=cfg.chunk_env)
    if cfg.backend == "bm25":
        idx = build_bm25_index(chunks=chunks, buckets=cfg.bm25_buckets)
        idx.save(str(out_path))
        return idx.fingerprint

    if cfg.backend == "numpy-cosine":
        idx = build_numpy_cosine_index(chunks=chunks, embedder=_make_embedder(cfg))
        idx.save(str(out_path))
        return idx.fingerprint

    raise ValueError(f"unknown index backend: {cfg.backend}")


__all__ = [
    "IndexBuildConfig",
    "build_index_from_csv",
    "ingest_csv_to_chunks",
    "ingest_docs_to_chunks",
]
