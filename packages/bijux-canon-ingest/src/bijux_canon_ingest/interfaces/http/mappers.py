# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Pure request and response mapping helpers for the HTTP boundary."""

from __future__ import annotations

from bijux_canon_ingest.application.service import AnswerPayload
from bijux_canon_ingest.core.types import Chunk, RawDoc
from bijux_canon_ingest.interfaces.http.models import (
    AskResponse,
    CandidateModel,
    ChunkOut,
    ChunkResponse,
    CitationModel,
    DocIn,
    IndexBuildResponse,
    RetrieveResponse,
)
from bijux_canon_ingest.retrieval.ports import Candidate


def raw_docs_from_http_docs(docs: list[DocIn]) -> list[RawDoc]:
    return [
        RawDoc(
            doc_id=doc.doc_id,
            title=doc.title or "",
            abstract=doc.text,
            categories=doc.category or "",
        )
        for doc in docs
    ]


def chunk_response_from_result(chunks: list[Chunk]) -> ChunkResponse:
    return ChunkResponse(
        chunks=[
            ChunkOut(
                doc_id=chunk.doc_id,
                text=chunk.text,
                start=chunk.start,
                end=chunk.end,
                metadata=dict(chunk.metadata),
                embedding=chunk.embedding if chunk.embedding else None,
                chunk_id=chunk.chunk_id,
            )
            for chunk in chunks
        ]
    )


def index_build_response(
    index_id: str, *, fingerprint: str, schema_version: int
) -> IndexBuildResponse:
    return IndexBuildResponse(
        index_id=index_id,
        fingerprint=fingerprint,
        schema_version=schema_version,
    )


def retrieve_response_from_candidates(candidates: list[Candidate]) -> RetrieveResponse:
    return RetrieveResponse(
        candidates=[
            CandidateModel(
                score=candidate.score,
                chunk={
                    "doc_id": candidate.chunk.doc_id,
                    "chunk_id": candidate.chunk.chunk_id,
                    "text": candidate.chunk.text,
                    "start": candidate.chunk.start,
                    "end": candidate.chunk.end,
                    "metadata": dict(candidate.chunk.metadata),
                },
                metadata=dict(candidate.metadata),
            )
            for candidate in candidates
        ]
    )


def ask_response_from_payload(answer: AnswerPayload) -> AskResponse:
    return AskResponse(
        answer=answer["answer"],
        citations=[
            CitationModel(
                doc_id=citation["doc_id"],
                chunk_id=citation["chunk_id"],
                start=citation["start"],
                end=citation["end"],
                text=citation["text"],
            )
            for citation in answer["citations"]
        ],
        candidates=[
            CandidateModel(
                score=context["score"],
                chunk={
                    "doc_id": context["doc_id"],
                    "chunk_id": context["chunk_id"],
                    "text": context["text"],
                    "start": context["start"],
                    "end": context["end"],
                    "metadata": {},
                },
                metadata={},
            )
            for context in answer["contexts"]
        ],
    )


__all__ = [
    "ask_response_from_payload",
    "chunk_response_from_result",
    "index_build_response",
    "raw_docs_from_http_docs",
    "retrieve_response_from_candidates",
]
