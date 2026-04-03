# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

# mypy: ignore-errors
"""Application service facade for in-memory indexes.

This module wires:
    clean -> chunk -> index -> retrieve -> (optional rerank) -> generate.

Both CLI and FastAPI boundaries call into this layer to avoid drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_ingest.application.index_runtime import (
    IndexBackend,
    StoredIndex,
    build_stored_index,
    load_stored_index,
    retrieve_blob_candidates,
    retrieve_candidates,
    save_stored_index,
)
from bijux_canon_ingest.retrieval.answering import ExtractiveAnswerer
from bijux_canon_ingest.retrieval.ports import Answer
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker
from bijux_canon_ingest.result.types import Err, Ok, Result


@dataclass(frozen=True, slots=True)
class IngestService:
    """Facade over index construction, persistence, retrieval, and answering."""

    answerer: ExtractiveAnswerer = ExtractiveAnswerer()
    reranker: LexicalOverlapReranker = LexicalOverlapReranker()
    profile: str = "default"

    def build_index(
        self,
        docs,
        backend: str = "bm25",
        chunk_size: int = 4096,
        overlap: int = 0,
        tail_policy: str = "emit_short",
    ) -> Result[StoredIndex, str]:
        return build_stored_index(
            docs=docs,
            backend=backend,
            chunk_size=chunk_size,
            overlap=overlap,
            tail_policy=tail_policy,
        )

    def save_index(self, index: StoredIndex, path: Path) -> Result[None, str]:
        return save_stored_index(index, path)

    def load_index(self, path: Path) -> Result[StoredIndex, str]:
        return load_stored_index(path)

    def retrieve(
        self,
        index: StoredIndex,
        query: str,
        top_k: int,
        filters: dict[str, str] | None = None,
    ):
        return retrieve_candidates(
            index=index,
            query=query,
            top_k=top_k,
            filters=filters,
            reranker=self.reranker,
        )

    def ask(
        self,
        index: StoredIndex,
        query: str,
        top_k: int,
        filters: dict[str, str] | None = None,
        rerank: bool = True,
    ) -> Result[dict[str, object], str]:
        retrieved = self.retrieve(
            index=index,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters or {},
        )
        if isinstance(retrieved, Err):
            return retrieved

        candidates = retrieved.value
        if not candidates:
            return Err("no candidates retrieved")
        if rerank:
            candidates = self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]
        return Ok(_answer_payload(candidates, top_k=top_k))

    def retrieve_blob(
        self,
        blob: bytes,
        query: str,
        top_k: int,
        filters: dict[str, str],
    ):
        return retrieve_blob_candidates(
            blob=blob,
            query=query,
            top_k=top_k,
            filters=filters,
        )

    def ask_blob(
        self,
        blob: bytes,
        query: str,
        top_k: int,
        filters: dict[str, str],
        rerank: bool = True,
    ) -> Result[Answer, str]:
        retrieved = self.retrieve_blob(
            blob=blob,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters,
        )
        if isinstance(retrieved, Err):
            return retrieved

        candidates = retrieved.value
        if rerank and candidates:
            candidates = self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]
        return Ok(self.answerer.generate(query=query, candidates=candidates))


def _answer_payload(candidates, *, top_k: int) -> dict[str, object]:
    top = candidates[0]
    contexts = [
        {
            "doc_id": candidate.doc_id,
            "text": candidate.text,
            "start": candidate.start,
            "end": candidate.end,
            "chunk_id": candidate.chunk_id,
            "score": candidate.score,
        }
        for candidate in candidates[: max(1, top_k)]
    ]
    citations = [
        {
            "doc_id": context["doc_id"],
            "chunk_id": context["chunk_id"],
            "start": context["start"],
            "end": context["end"],
            "text": context["text"],
        }
        for context in contexts
    ]
    return {
        "answer": top.chunk.text,
        "citations": citations,
        "contexts": contexts,
        "candidates": contexts,
    }


__all__ = ["IndexBackend", "IngestService", "StoredIndex"]
