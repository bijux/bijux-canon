# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed answer payload contracts for application-facing retrieval flows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from bijux_canon_ingest.retrieval.ports import Candidate


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


def answer_payload_from_candidates(
    candidates: Sequence[Candidate], *, top_k: int
) -> AnswerPayload:
    """Build the stable application answer payload from ranked candidates."""

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
    "answer_payload_from_candidates",
]
