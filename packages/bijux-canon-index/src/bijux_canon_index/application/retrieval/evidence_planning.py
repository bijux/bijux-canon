# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded question decomposition for content-first evidence retrieval."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .multi_query import MultiQueryPlan, MultiQueryPolicy, plan_subqueries


EVIDENCE_PLANNING_POLICY_ID = "bijux.canon.index.evidence-planning.content-v1"

_QUESTION_WORD = r"(?:what|which|how|where|why)"
_SKEPTICAL_TERMS = re.compile(
    r"\b(?:all|always|disagree|every|fail|falsely|guarantee|mandatory|prove|simple)\b"
    r"|\bunknown\s+handling\b|\blimitation\b",
    re.IGNORECASE,
)
_COMPARATIVE_TERMS = re.compile(
    r"\b(?:combine\s+the\s+studies|disagree|guarantee|prove)\b"
    r"|\bstudies['’]\s+findings\b|\bevery\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class EvidenceQueryPlan:
    """Transparent subqueries and the required document-evidence breadth."""

    schema_version: str
    planning_policy_id: str
    document_breadth: int
    facet_subquery_ids: tuple[str, ...]
    multi_query: MultiQueryPlan

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.retrieval.evidence_query_plan.v1":
            raise ValueError("evidence query plan schema is unsupported")
        if not 1 <= self.document_breadth <= 4:
            raise ValueError("evidence document breadth must be within 1..4")
        admitted = {item.subquery_id for item in self.multi_query.subqueries}
        if not set(self.facet_subquery_ids) <= admitted:
            raise ValueError("evidence facets must resolve to admitted subqueries")


def _list_items(value: str, *, conjunction: str) -> tuple[str, ...]:
    normalized = re.sub(
        rf"\b{conjunction}\b",
        ",",
        value,
        flags=re.IGNORECASE,
    )
    return tuple(
        item.strip(" ,")
        for item in normalized.split(",")
        if item.strip(" ,")
    )


def _explicit_facets(query_text: str) -> tuple[str, ...]:
    across = re.search(
        rf"\bacross\s+(.+?),\s*{_QUESTION_WORD}\b",
        query_text,
        re.IGNORECASE,
    )
    if across is not None:
        return tuple(
            item for item in _list_items(across.group(1), conjunction="and")
            if len(item.split()) >= 2
        )[:4]
    paired_studies = re.search(
        r"\b([^?,]{1,100}?)\s+and\s+([^?,]{1,100}?)\s+studies\b",
        query_text,
        re.IGNORECASE,
    )
    if paired_studies is not None:
        return tuple(
            item.strip(" ,")
            for item in paired_studies.groups()
            if item.strip(" ,")
        )
    based_on = re.search(
        r"\bbased\s+on\s+(.+?)(?:\?|$)",
        query_text,
        re.IGNORECASE,
    )
    if based_on is not None:
        return _list_items(based_on.group(1), conjunction="or")[:4]
    return ()


def plan_evidence_query(
    query_text: str,
    *,
    max_subqueries: int = 8,
    per_query_top_k: int = 500,
    top_k: int = 10,
) -> EvidenceQueryPlan:
    """Derive general evidence needs from question structure, never identities."""

    normalized = query_text.strip()
    if not normalized:
        raise ValueError("evidence planning query must not be empty")
    facets = _explicit_facets(normalized)
    generated: list[tuple[str, str]] = [
        (
            f"{facet} evidence result limitation",
            "explicit coordinated evidence facet",
        )
        for facet in facets
    ]
    if _SKEPTICAL_TERMS.search(normalized):
        generated.append(
            (
                normalized
                + " contradictory evidence limitation exception boundary condition"
                " not reliable indistinguishable case by case",
                "bounded counterevidence and boundary-condition need",
            )
        )
    if re.search(
        r"\b(?:experimental|how|method|recommend)\b",
        normalized,
        re.IGNORECASE,
    ):
        generated.append(
            (
                normalized
                + " experiment methods results recommendation conclusion",
                "method, result, and recommendation need",
            )
        )
    generated.append(
        (
            normalized + " result conclusion quantitative evidence",
            "answer-bearing result and conclusion need",
        )
    )
    policy = MultiQueryPolicy(
        max_subqueries=max_subqueries,
        per_query_top_k=per_query_top_k,
        top_k=top_k,
        rank_constant=5,
    )
    multi_query = plan_subqueries(
        normalized,
        policy=policy,
        generated_queries=tuple(generated),
    )
    generated_subqueries = tuple(
        item for item in multi_query.subqueries if item.ordinal > 1
    )
    facet_ids = tuple(
        item.subquery_id for item in generated_subqueries[: len(facets)]
    )
    if facets:
        document_breadth = len(facets)
    elif _COMPARATIVE_TERMS.search(normalized):
        document_breadth = 3
    elif re.search(r"\b(?:fail|why\s+can)\b", normalized, re.IGNORECASE):
        document_breadth = 2
    else:
        document_breadth = 1
    return EvidenceQueryPlan(
        "bijux.canon.retrieval.evidence_query_plan.v1",
        EVIDENCE_PLANNING_POLICY_ID,
        min(4, document_breadth),
        facet_ids,
        multi_query,
    )


__all__ = [
    "EVIDENCE_PLANNING_POLICY_ID",
    "EvidenceQueryPlan",
    "plan_evidence_query",
]
