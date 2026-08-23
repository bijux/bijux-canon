# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Hierarchical passage ranking over bounded content-derived evidence needs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from .evidence_planning import EvidenceQueryPlan
from .fusion import FusedCandidate, RrfFusionBatch
from .lexical import LexicalCandidateBatch
from .reranking import (
    RerankBatch,
    RerankedCandidate,
    RerankOutcome,
)


PLANNED_RERANK_POLICY_ID = "bijux.canon.index.planned-rerank.content-v1"


@dataclass(frozen=True, slots=True)
class PlannedRerankPolicy:
    """Versioned weights for document routing and answer-passage selection."""

    policy_id: str = PLANNED_RERANK_POLICY_ID
    rank_constant: int = 5
    base_rank_weight: float = 1.0
    evidence_need_weight: float = 0.25
    abstract_weight: float = 0.1
    answer_section_weight: float = 0.05
    introduction_weight: float = 0.05
    early_ordinal_weight: float = 0.6
    early_ordinal_priors: tuple[float, ...] = (0.0, 0.8, 1.0, 0.6)

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not 1 <= self.rank_constant <= 10_000:
            raise ValueError("planned rerank policy identity or rank constant is invalid")
        if any(
            not math.isfinite(value) or value < 0
            for value in (
                self.base_rank_weight,
                self.evidence_need_weight,
                self.abstract_weight,
                self.answer_section_weight,
                self.introduction_weight,
                self.early_ordinal_weight,
                *self.early_ordinal_priors,
            )
        ):
            raise ValueError("planned rerank weights must be finite and non-negative")
        if not self.base_rank_weight or not self.evidence_need_weight:
            raise ValueError("planned rerank retrieval weights must be positive")

    @property
    def identity_sha256(self) -> str:
        """Return the immutable identity of all ranking behavior."""

        return _sha256(asdict(self))


@dataclass(frozen=True, slots=True)
class EvidencePassageContext:
    """Content structure needed to distinguish routing from answer passages."""

    chunk_id: str
    document_id: str
    ordinal: int
    block_roles: tuple[str, ...]
    section_paths: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.document_id or self.ordinal < 0:
            raise ValueError("evidence passage context identity is invalid")
        if not self.block_roles or any(not item for item in self.block_roles):
            raise ValueError("evidence passage context requires block roles")
        if len(self.block_roles) != len(self.section_paths):
            raise ValueError("evidence passage roles and section paths must align")


def _sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rank_map(batch: LexicalCandidateBatch) -> dict[str, int]:
    return {
        item.chunk_id: item.source_rank
        for item in batch.decisions
    }


def rerank_planned_evidence(
    fusion: RrfFusionBatch,
    *,
    plan: EvidenceQueryPlan,
    lexical_by_subquery_id: dict[str, LexicalCandidateBatch],
    passages: tuple[EvidencePassageContext, ...],
    top_k: int,
    policy: PlannedRerankPolicy = PlannedRerankPolicy(),
) -> RerankBatch:
    """Rank answer-bearing passages while preserving the retrieved candidate set."""

    if not 1 <= top_k <= len(fusion.hits):
        raise ValueError("planned rerank top_k must fit the fused candidate pool")
    subqueries = plan.multi_query.subqueries
    if set(lexical_by_subquery_id) != {item.subquery_id for item in subqueries}:
        raise ValueError("planned rerank requires one lexical result per subquery")
    if any(
        batch.generation_id != fusion.generation_id
        or batch.query_text_sha256 != subquery.text_sha256
        for subquery in subqueries
        for batch in (lexical_by_subquery_id[subquery.subquery_id],)
    ):
        raise ValueError("planned rerank subquery provenance differs from the plan")
    base_rank = {item.chunk_id: item.rank for item in fusion.hits}
    if len(base_rank) != len(fusion.hits):
        raise ValueError("planned rerank fused candidates must be unique")
    context = {item.chunk_id: item for item in passages}
    if len(context) != len(passages) or set(context) != set(base_rank):
        raise ValueError("planned rerank passage context must resolve every candidate")
    if any(
        item.document_id != context[item.chunk_id].document_id
        or item.ordinal != context[item.chunk_id].ordinal
        for item in fusion.hits
    ):
        raise ValueError("planned rerank passage context differs from retrieval truth")
    need_ranks = tuple(
        _rank_map(lexical_by_subquery_id[item.subquery_id]) for item in subqueries
    )
    by_document: dict[str, list[FusedCandidate]] = defaultdict(list)
    for item in fusion.hits:
        by_document[item.document_id].append(item)

    def document_score(document_id: str, need_indexes: tuple[int, ...]) -> float:
        candidates = by_document[document_id]
        score = policy.base_rank_weight / (
            policy.rank_constant + min(base_rank[item.chunk_id] for item in candidates)
        )
        for need_index in need_indexes:
            ranks = need_ranks[need_index]
            observed = [
                ranks[item.chunk_id]
                for item in candidates
                if item.chunk_id in ranks
            ]
            if observed:
                score += policy.evidence_need_weight / (
                    policy.rank_constant + min(observed)
                )
        return score

    documents: list[str] = []
    facet_indexes = tuple(
        index
        for index, item in enumerate(subqueries)
        if item.subquery_id in plan.facet_subquery_ids
    )
    for need_index in facet_indexes:
        ranked_documents = sorted(
            by_document,
            key=lambda document_id: (
                -document_score(document_id, (need_index,)),
                document_id,
            ),
        )
        documents.append(
            next(
                (
                    document_id
                    for document_id in ranked_documents
                    if document_id not in documents
                ),
                ranked_documents[0],
            )
        )
    all_need_indexes = tuple(range(len(need_ranks)))
    for document_id in sorted(
        by_document,
        key=lambda item: (-document_score(item, all_need_indexes), item),
    ):
        if len(documents) >= plan.document_breadth:
            break
        if document_id not in documents:
            documents.append(document_id)

    def passage_score(item: FusedCandidate) -> float:
        score = policy.base_rank_weight / (
            policy.rank_constant + base_rank[item.chunk_id]
        )
        for ranks in need_ranks:
            rank = ranks.get(item.chunk_id)
            if rank is not None:
                score += policy.evidence_need_weight / (
                    policy.rank_constant + rank
                )
        passage = context[item.chunk_id]
        roles = {role.casefold() for role in passage.block_roles}
        sections = {
            value.casefold()
            for path in passage.section_paths
            for value in path
        }
        if "abstract" in roles:
            score += policy.abstract_weight
        if any(
            marker in section
            for section in sections
            for marker in ("conclusion", "discussion", "limitation", "result")
        ):
            score += policy.answer_section_weight
        if any("introduction" in section for section in sections):
            score += policy.introduction_weight
        if item.ordinal < len(policy.early_ordinal_priors):
            score += (
                policy.early_ordinal_weight
                * policy.early_ordinal_priors[item.ordinal]
            )
        return score

    remaining = {
        document_id: sorted(
            by_document[document_id],
            key=lambda item: (-passage_score(item), item.ordinal, item.chunk_id),
        )
        for document_id in documents
    }
    ordered: list[FusedCandidate] = []
    for document_id in documents:
        if remaining[document_id]:
            ordered.append(remaining[document_id].pop(0))
    while len(ordered) < top_k and any(remaining.values()):
        choices = tuple(items[0] for items in remaining.values() if items)
        selected_passage = max(
            choices,
            key=lambda item: (passage_score(item), -item.ordinal, item.chunk_id),
        )
        ordered.append(selected_passage)
        remaining[selected_passage.document_id].pop(0)
    if len(ordered) < top_k:
        ordered.extend(
            item
            for item in fusion.hits
            if item not in ordered
        )
    selected_candidates = tuple(ordered[:top_k])
    candidates = tuple(
        RerankedCandidate(
            rank=rank,
            retrieval_rank=item.rank,
            chunk_id=item.chunk_id,
            fused_score=item.fused_score,
            rerank_score=passage_score(item),
            candidate=item,
        )
        for rank, item in enumerate(selected_candidates, start=1)
    )
    return RerankBatch(
        schema_version="bijux.canon.retrieval.rerank.v1",
        generation_id=fusion.generation_id,
        query_text_sha256=fusion.query_text_sha256,
        policy_sha256=policy.identity_sha256,
        outcome=RerankOutcome.applied,
        reranker_artifact_id=plan.multi_query.plan_id,
        provider="bijux-canon-index",
        model_id=policy.policy_id,
        provider_request_id=None,
        usage=(
            ("evidence_needs", len(subqueries)),
            ("selected_documents", len(documents)),
        ),
        latency_ms=0.0,
        failure_kind=None,
        candidates=candidates,
    )


__all__ = [
    "EvidencePassageContext",
    "PLANNED_RERANK_POLICY_ID",
    "PlannedRerankPolicy",
    "rerank_planned_evidence",
]
