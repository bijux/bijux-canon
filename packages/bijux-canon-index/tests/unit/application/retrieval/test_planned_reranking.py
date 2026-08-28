# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib

import pytest

from bijux_canon_index.application import (
    EvidencePassageContext,
    FusedCandidate,
    LexicalCandidateBatch,
    LexicalCandidateDecision,
    LexicalCandidateDisposition,
    LexicalCandidateOutcome,
    RerankOutcome,
    RrfFusionBatch,
    plan_evidence_query,
    rerank_planned_evidence,
)


def _chunk(document: int, ordinal: int) -> str:
    return f"doc-{document}-chunk-{ordinal}"


def _fusion() -> RrfFusionBatch:
    ordered = [
        _chunk(1, 0),
        _chunk(1, 1),
        _chunk(2, 0),
        _chunk(3, 0),
        _chunk(2, 1),
        _chunk(3, 1),
        _chunk(1, 2),
        _chunk(2, 2),
        _chunk(3, 2),
    ]
    hits = tuple(
        FusedCandidate(
            artifact_id="sha256:" + hashlib.sha256(chunk_id.encode()).hexdigest(),
            rank=rank,
            fused_score=1.0 / rank,
            chunk_id=chunk_id,
            document_id=chunk_id.split("-chunk-")[0],
            ordinal=int(chunk_id.rsplit("-", maxsplit=1)[1]),
            source_text_sha256=hashlib.sha256(chunk_id.encode()).hexdigest(),
            contributions=(),
        )
        for rank, chunk_id in enumerate(ordered, start=1)
    )
    return RrfFusionBatch("v1", "generation", "a" * 64, "b" * 64, "c" * 64, hits)


def _lexical(query_hash: str, ordered: tuple[str, ...]) -> LexicalCandidateBatch:
    decisions = tuple(
        LexicalCandidateDecision(
            source_rank=rank,
            output_rank=rank,
            score=1.0 / rank,
            chunk_id=chunk_id,
            document_id=chunk_id.split("-chunk-")[0],
            ordinal=int(chunk_id.rsplit("-", maxsplit=1)[1]),
            source_text_sha256=hashlib.sha256(chunk_id.encode()).hexdigest(),
            disposition=LexicalCandidateDisposition.included,
        )
        for rank, chunk_id in enumerate(ordered, start=1)
    )
    return LexicalCandidateBatch(
        "v1",
        "generation",
        "segment",
        "tokenizer",
        query_hash,
        hashlib.sha256(b"{}").hexdigest(),
        len(ordered),
        len(ordered),
        LexicalCandidateOutcome.success,
        decisions,
    )


def _passages() -> tuple[EvidencePassageContext, ...]:
    return tuple(
        EvidencePassageContext(
            hit.chunk_id,
            hit.document_id,
            hit.ordinal,
            ("abstract",) if hit.ordinal == 2 else ("paragraph",),
            ((),) if hit.ordinal == 2 else (("Introduction",),),
        )
        for hit in _fusion().hits
    )


def test_planned_rerank_routes_facets_then_selects_answer_bearing_passages() -> None:
    plan = plan_evidence_query(
        "Across alpha material, beta material, and gamma material, what results "
        "and limitations were reported?",
        per_query_top_k=9,
        top_k=5,
    )
    facet_documents = (1, 2, 3)
    lexical = {}
    for subquery in plan.multi_query.subqueries:
        if subquery.subquery_id in plan.facet_subquery_ids:
            document = facet_documents[
                plan.facet_subquery_ids.index(subquery.subquery_id)
            ]
            first = tuple(_chunk(document, ordinal) for ordinal in (2, 1, 0))
        else:
            first = tuple(hit.chunk_id for hit in _fusion().hits)
        remainder = tuple(
            hit.chunk_id for hit in _fusion().hits if hit.chunk_id not in first
        )
        lexical[subquery.subquery_id] = _lexical(
            subquery.text_sha256,
            first + remainder,
        )

    batch = rerank_planned_evidence(
        _fusion(),
        plan=plan,
        lexical_by_subquery_id=lexical,
        passages=_passages(),
        top_k=5,
    )

    assert batch.outcome is RerankOutcome.applied
    assert [item.chunk_id for item in batch.candidates[:3]] == [
        _chunk(1, 2),
        _chunk(2, 2),
        _chunk(3, 2),
    ]
    assert {item.chunk_id for item in batch.candidates} <= {
        item.chunk_id for item in _fusion().hits
    }
    assert batch.usage == (("evidence_needs", 5), ("selected_documents", 3))


def test_planned_rerank_refuses_missing_or_mismatched_subquery_evidence() -> None:
    plan = plan_evidence_query("What result was reported?", per_query_top_k=9)
    subquery = plan.multi_query.subqueries[0]
    lexical = {
        subquery.subquery_id: _lexical(
            subquery.text_sha256,
            tuple(hit.chunk_id for hit in _fusion().hits),
        )
    }

    with pytest.raises(ValueError, match="one lexical result"):
        rerank_planned_evidence(
            _fusion(),
            plan=plan,
            lexical_by_subquery_id=lexical,
            passages=_passages(),
            top_k=5,
        )
