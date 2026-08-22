# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded transparent multi-query retrieval with exact hit attribution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import Enum, StrEnum
import hashlib
import json

from .locators import (
    CitationReadyHit,
    CitationResolutionBatch,
    CitationRetrievalMode,
)


def _canonical_json(value: object) -> bytes:
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, dict):
        value = {str(key): _json_value(item) for key, item in value.items()}
    elif isinstance(value, list | tuple):
        value = [_json_value(item) for item in value]
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


class SubqueryOrigin(StrEnum):
    """Transparent reason one subquery entered a multi-query plan."""

    original = "original"
    supplied = "supplied"
    generated_facet = "generated_facet"


class SubqueryDisposition(StrEnum):
    """Whether a proposed query entered the bounded execution plan."""

    included = "included"
    duplicate = "duplicate"
    fanout_limit = "fanout_limit"


class MultiQueryOutcome(StrEnum):
    """Typed sufficiency of one completed multi-query execution."""

    success = "success"
    no_matches = "no_matches"


@dataclass(frozen=True, slots=True)
class MultiQueryPolicy:
    """Hard fan-out, per-query, total-result, and input-size bounds."""

    max_subqueries: int
    per_query_top_k: int
    top_k: int
    rank_constant: int = 60
    max_query_characters: int = 4096

    def __post_init__(self) -> None:
        if not 1 <= self.max_subqueries <= 32:
            raise ValueError("multi-query fan-out must be within 1..32")
        if not 1 <= self.per_query_top_k <= 1000:
            raise ValueError("multi-query per-query top_k must be within 1..1000")
        if not 1 <= self.top_k <= 1000:
            raise ValueError("multi-query final top_k must be within 1..1000")
        if not 1 <= self.rank_constant <= 10_000:
            raise ValueError("multi-query rank constant must be within 1..10000")
        if not 1 <= self.max_query_characters <= 100_000:
            raise ValueError("multi-query text bound must be within 1..100000")


@dataclass(frozen=True, slots=True)
class PlannedSubquery:
    """One included query with its stable identity and derivation."""

    ordinal: int
    subquery_id: str
    text: str
    text_sha256: str
    origin: SubqueryOrigin
    derivation: str


@dataclass(frozen=True, slots=True)
class SubqueryPlanDecision:
    """Auditable disposition for every original, supplied, or generated query."""

    proposal_ordinal: int
    text: str
    text_sha256: str
    origin: SubqueryOrigin
    derivation: str
    disposition: SubqueryDisposition
    subquery_id: str | None
    duplicate_of_subquery_id: str | None


@dataclass(frozen=True, slots=True)
class MultiQueryPlan:
    """Bounded deterministic plan retaining included and excluded proposals."""

    schema_version: str
    policy_sha256: str
    plan_id: str
    subqueries: tuple[PlannedSubquery, ...]
    decisions: tuple[SubqueryPlanDecision, ...]


@dataclass(frozen=True, slots=True)
class SubqueryHitAttribution:
    """One subquery's exact contribution to a deduplicated evidence hit."""

    subquery_id: str
    subquery_ordinal: int
    subquery_text_sha256: str
    source_rank: int
    source_retrieval_rank: int
    source_retrieval_score: float
    reciprocal_rank_score: float
    citation_artifact_id: str


@dataclass(frozen=True, slots=True)
class MultiQueryHit:
    """One content-deduplicated citation with every subquery attribution."""

    artifact_id: str
    rank: int
    aggregate_score: float
    content_sha256: str
    retained_chunk_id: str
    duplicate_chunk_ids: tuple[str, ...]
    citation: CitationReadyHit
    attributions: tuple[SubqueryHitAttribution, ...]


@dataclass(frozen=True, slots=True)
class MultiQueryBatch:
    """Final bounded ranking linked to all subquery executions."""

    schema_version: str
    generation_id: str
    retrieval_mode: CitationRetrievalMode
    plan_id: str
    outcome: MultiQueryOutcome
    executed_subquery_count: int
    raw_hit_count: int
    deduplicated_hit_count: int
    result_limit_excluded_count: int
    hits: tuple[MultiQueryHit, ...]


MultiQueryExecutor = Callable[[PlannedSubquery, int], CitationResolutionBatch]


def plan_subqueries(
    query_text: str,
    *,
    policy: MultiQueryPolicy,
    supplied_subqueries: tuple[str, ...] = (),
    generated_facets: tuple[str, ...] = (),
) -> MultiQueryPlan:
    """Create a transparent bounded plan without any provider dependency."""

    if not query_text.strip():
        raise ValueError("multi-query original query must not be empty")
    proposals = [(query_text, SubqueryOrigin.original, "original request")]
    proposals.extend(
        (text, SubqueryOrigin.supplied, "caller-supplied subquery")
        for text in supplied_subqueries
    )
    proposals.extend(
        (
            f"{query_text.rstrip()} {facet.strip()}",
            SubqueryOrigin.generated_facet,
            f"deterministic facet suffix: {facet.strip()}",
        )
        for facet in generated_facets
    )
    included: list[PlannedSubquery] = []
    decisions: list[SubqueryPlanDecision] = []
    by_text: dict[str, str] = {}
    for proposal_ordinal, (text, origin, derivation) in enumerate(proposals, start=1):
        normalized = text.strip()
        if not normalized:
            raise ValueError("multi-query proposals must not be empty")
        if len(normalized) > policy.max_query_characters:
            raise ValueError("multi-query proposal exceeds the query text bound")
        text_sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        duplicate_of = by_text.get(normalized)
        if duplicate_of is not None:
            disposition = SubqueryDisposition.duplicate
            subquery_id = None
        elif len(included) == policy.max_subqueries:
            disposition = SubqueryDisposition.fanout_limit
            subquery_id = None
        else:
            ordinal = len(included) + 1
            subquery_id = _identity(
                {
                    "derivation": derivation,
                    "ordinal": ordinal,
                    "origin": origin.value,
                    "text_sha256": text_sha256,
                }
            )
            included.append(
                PlannedSubquery(
                    ordinal,
                    subquery_id,
                    normalized,
                    text_sha256,
                    origin,
                    derivation,
                )
            )
            by_text[normalized] = subquery_id
            disposition = SubqueryDisposition.included
        decisions.append(
            SubqueryPlanDecision(
                proposal_ordinal,
                normalized,
                text_sha256,
                origin,
                derivation,
                disposition,
                subquery_id,
                duplicate_of,
            )
        )
    policy_sha256 = hashlib.sha256(_canonical_json(asdict(policy))).hexdigest()
    plan_payload = {
        "decisions": [asdict(item) for item in decisions],
        "policy_sha256": policy_sha256,
        "subqueries": [asdict(item) for item in included],
    }
    return MultiQueryPlan(
        "bijux.canon.retrieval.multi_query_plan.v1",
        policy_sha256,
        _identity(plan_payload),
        tuple(included),
        tuple(decisions),
    )


def execute_multi_query(
    plan: MultiQueryPlan,
    *,
    generation_id: str,
    retrieval_mode: CitationRetrievalMode,
    policy: MultiQueryPolicy,
    executor: MultiQueryExecutor,
) -> MultiQueryBatch:
    """Execute every admitted subquery once and fuse exact citation evidence."""

    expected_policy = hashlib.sha256(_canonical_json(asdict(policy))).hexdigest()
    if plan.policy_sha256 != expected_policy:
        raise ValueError("multi-query plan and execution policies differ")
    if not isinstance(retrieval_mode, CitationRetrievalMode):
        raise ValueError("multi-query retrieval mode is unsupported")
    if len(plan.subqueries) > policy.max_subqueries:
        raise ValueError("multi-query plan exceeds the execution fan-out bound")
    results = []
    for subquery in plan.subqueries:
        batch = executor(subquery, policy.per_query_top_k)
        if batch.generation_id != generation_id:
            raise ValueError("multi-query result generation identity differs")
        if batch.query_text_sha256 != subquery.text_sha256:
            raise ValueError("multi-query result query identity differs")
        if batch.retrieval_mode is not retrieval_mode:
            raise ValueError("multi-query result retrieval mode differs")
        if len(batch.hits) > policy.per_query_top_k:
            raise ValueError("multi-query result exceeds the per-query bound")
        results.append((subquery, batch))

    grouped: dict[str, list[tuple[PlannedSubquery, CitationReadyHit]]] = {}
    for subquery, batch in results:
        for hit in batch.hits:
            grouped.setdefault(hit.content_sha256, []).append((subquery, hit))

    fused = []
    for content_sha256, entries in grouped.items():
        ordered = sorted(
            entries,
            key=lambda item: (
                item[1].rank,
                item[0].ordinal,
                item[1].chunk_id,
                item[1].artifact_id,
            ),
        )
        retained_subquery, retained = ordered[0]
        del retained_subquery
        attributions = tuple(
            SubqueryHitAttribution(
                subquery.subquery_id,
                subquery.ordinal,
                subquery.text_sha256,
                hit.rank,
                hit.retrieval_rank,
                hit.retrieval_score,
                1.0 / (policy.rank_constant + hit.rank),
                hit.artifact_id,
            )
            for subquery, hit in sorted(
                entries,
                key=lambda item: (item[0].ordinal, item[1].rank, item[1].chunk_id),
            )
        )
        score = sum(item.reciprocal_rank_score for item in attributions)
        duplicate_ids = tuple(
            sorted({hit.chunk_id for _, hit in entries} - {retained.chunk_id})
        )
        fused.append(
            (
                score,
                retained.chunk_id,
                content_sha256,
                retained,
                duplicate_ids,
                attributions,
            )
        )
    fused.sort(key=lambda item: (-item[0], item[1], item[2]))
    hits = []
    for rank, (
        score,
        retained_chunk_id,
        content_sha256,
        citation,
        duplicate_ids,
        attributions,
    ) in enumerate(fused[: policy.top_k], start=1):
        hit_payload = {
            "attributions": [asdict(item) for item in attributions],
            "content_sha256": content_sha256,
            "plan_id": plan.plan_id,
            "rank": rank,
            "retained_chunk_id": retained_chunk_id,
        }
        hits.append(
            MultiQueryHit(
                _identity(hit_payload),
                rank,
                score,
                content_sha256,
                retained_chunk_id,
                duplicate_ids,
                citation,
                attributions,
            )
        )
    raw_count = sum(len(batch.hits) for _, batch in results)
    return MultiQueryBatch(
        "bijux.canon.retrieval.multi_query_batch.v1",
        generation_id,
        retrieval_mode,
        plan.plan_id,
        MultiQueryOutcome.success if hits else MultiQueryOutcome.no_matches,
        len(results),
        raw_count,
        len(grouped),
        max(0, len(grouped) - len(hits)),
        tuple(hits),
    )


__all__ = [
    "MultiQueryBatch",
    "MultiQueryExecutor",
    "MultiQueryHit",
    "MultiQueryOutcome",
    "MultiQueryPlan",
    "MultiQueryPolicy",
    "PlannedSubquery",
    "SubqueryDisposition",
    "SubqueryHitAttribution",
    "SubqueryOrigin",
    "SubqueryPlanDecision",
    "execute_multi_query",
    "plan_subqueries",
]
