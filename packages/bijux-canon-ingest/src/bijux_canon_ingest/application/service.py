# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application service facade for in-memory indexes.

This module wires:
    clean -> chunk -> index -> retrieve -> (optional rerank) -> generate.

Both CLI and FastAPI boundaries call into this layer to avoid drift.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

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
from bijux_canon_ingest.retrieval.ports import Answer, Candidate
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker
from bijux_canon_ingest.result.types import Err, Ok, Result


class CandidatePayload(TypedDict):
    doc_id: str
    text: str
    start: int
    end: int
    chunk_id: str
    score: float


class CitationPayload(TypedDict):
    doc_id: str
    chunk_id: str
    start: int
    end: int
    text: str


class AnswerPayload(TypedDict):
    answer: str
    citations: list[CitationPayload]
    contexts: list[CandidatePayload]
    candidates: list[CandidatePayload]


@dataclass(frozen=True, slots=True)
class IngestService:
    """Facade over index construction, persistence, retrieval, and answering."""

    answerer: ExtractiveAnswerer = ExtractiveAnswerer()
    reranker: LexicalOverlapReranker = LexicalOverlapReranker()
    profile: str = "default"

    def build_index(
        self,
        docs: Iterable[object],
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
        filters: Mapping[str, str] | None = None,
    ) -> Result[list[Candidate], str]:
        return retrieve_candidates(
            index=index,
            query=query,
            top_k=top_k,
            filters=dict(filters or {}),
            reranker=self.reranker,
        )

    def ask(
        self,
        index: StoredIndex,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        rerank: bool = True,
    ) -> Result[AnswerPayload, str]:
        retrieved = self.retrieve(
            index=index,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters,
        )
        if isinstance(retrieved, Err):
            return Err(retrieved.error)

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
        filters: Mapping[str, str] | None = None,
    ) -> Result[list[Candidate], str]:
        return retrieve_blob_candidates(
            blob=blob,
            query=query,
            top_k=top_k,
            filters=dict(filters or {}),
        )

    def ask_blob(
        self,
        blob: bytes,
        query: str,
        top_k: int,
        filters: Mapping[str, str] | None = None,
        rerank: bool = True,
    ) -> Result[Answer, str]:
        retrieved = self.retrieve_blob(
            blob=blob,
            query=query,
            top_k=max(top_k, 10 if rerank else top_k),
            filters=filters,
        )
        if isinstance(retrieved, Err):
            return Err(retrieved.error)

        candidates = retrieved.value
        if rerank and candidates:
            candidates = self.reranker.rerank(query=query, candidates=candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]
        return Ok(self.answerer.generate(query=query, candidates=candidates))


def _answer_payload(candidates: Sequence[Candidate], *, top_k: int) -> AnswerPayload:
    top = candidates[0]
    contexts: list[CandidatePayload] = [
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
    citations: list[CitationPayload] = [
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


__all__ = [
    "AnswerPayload",
    "CandidatePayload",
    "CitationPayload",
    "IndexBackend",
    "IngestService",
    "StoredIndex",
]
