# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic lineage deduplication and source/section diversity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
import math

from .fusion import FusedCandidate, RrfFusionBatch


class DeduplicationKey(str, Enum):
    """Stable lineage identity used to collapse evidence."""

    content_hash = "content_hash"
    source_span = "source_span"


class EvidenceSelectionDisposition(str, Enum):
    """Why a fused candidate was selected or excluded."""

    selected = "selected"
    duplicate = "duplicate"
    source_limit = "source_limit"
    section_limit = "section_limit"
    result_limit = "result_limit"


@dataclass(frozen=True, slots=True)
class EvidenceLineage:
    """Stable source ownership and deduplication identities for one chunk."""

    chunk_id: str
    content_hash: str
    source_span: str
    source_id: str
    section_id: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.chunk_id,
                self.content_hash,
                self.source_span,
                self.source_id,
                self.section_id,
            )
        ):
            raise ValueError("evidence lineage identities must be complete")


@dataclass(frozen=True, slots=True)
class EvidenceDeduplicationPolicy:
    """Whether and how equivalent evidence is collapsed."""

    enabled: bool = True
    lineage_key: DeduplicationKey = DeduplicationKey.content_hash

    def __post_init__(self) -> None:
        if not isinstance(self.lineage_key, DeduplicationKey):
            raise ValueError("deduplication lineage key is unsupported")


@dataclass(frozen=True, slots=True)
class EvidenceDiversityPolicy:
    """Optional deterministic caps on source and section concentration."""

    enabled: bool = False
    maximum_per_source: int = 1000
    maximum_per_section: int = 1000

    def __post_init__(self) -> None:
        if min(self.maximum_per_source, self.maximum_per_section) <= 0:
            raise ValueError("diversity limits must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceSelectionPolicy:
    """Complete post-fusion selection contract."""

    top_k: int
    deduplication: EvidenceDeduplicationPolicy = EvidenceDeduplicationPolicy()
    diversity: EvidenceDiversityPolicy = EvidenceDiversityPolicy()

    def __post_init__(self) -> None:
        if not 1 <= self.top_k <= 1000:
            raise ValueError("evidence selection top_k must be within 1..1000")


@dataclass(frozen=True, slots=True)
class EvidenceSelectionDecision:
    """Auditable disposition for every fused input candidate."""

    input_rank: int
    output_rank: int | None
    chunk_id: str
    fused_score: float
    disposition: EvidenceSelectionDisposition
    lineage_value: str
    retained_chunk_id: str | None


@dataclass(frozen=True, slots=True)
class EvidenceSelectionBatch:
    """Selected evidence plus explicit relevance-loss accounting."""

    schema_version: str
    generation_id: str
    query_text_sha256: str
    policy_sha256: str
    input_ranking_sha256: str
    candidates: tuple[FusedCandidate, ...]
    decisions: tuple[EvidenceSelectionDecision, ...]
    duplicate_count: int
    diversity_excluded_count: int
    result_limit_excluded_count: int
    excluded_fused_score: float


def _sha256_json(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _lineage_value(
    lineage: EvidenceLineage,
    key: DeduplicationKey,
) -> str:
    return (
        lineage.content_hash
        if key is DeduplicationKey.content_hash
        else lineage.source_span
    )


def select_evidence(
    fusion: RrfFusionBatch,
    lineage: tuple[EvidenceLineage, ...],
    *,
    policy: EvidenceSelectionPolicy,
) -> EvidenceSelectionBatch:
    """Select evidence in fused order without hiding any excluded relevance."""

    if any(not math.isfinite(hit.fused_score) for hit in fusion.hits):
        raise ValueError("fused evidence scores must be finite")
    if tuple(hit.rank for hit in fusion.hits) != tuple(range(1, len(fusion.hits) + 1)):
        raise ValueError("fused evidence ranks must be unique and contiguous")
    by_chunk = {item.chunk_id: item for item in lineage}
    hit_ids = {hit.chunk_id for hit in fusion.hits}
    if len(by_chunk) != len(lineage) or set(by_chunk) != hit_ids:
        raise ValueError("evidence lineage must resolve every fused chunk exactly once")

    selected: list[FusedCandidate] = []
    decisions = []
    retained_by_lineage: dict[str, str] = {}
    source_counts: dict[str, int] = {}
    section_counts: dict[str, int] = {}
    duplicate_count = 0
    diversity_count = 0
    result_limit_count = 0
    excluded_score = 0.0

    for hit in fusion.hits:
        item = by_chunk[hit.chunk_id]
        lineage_value = _lineage_value(item, policy.deduplication.lineage_key)
        retained_chunk_id = retained_by_lineage.get(lineage_value)
        output_rank: int | None = None
        if policy.deduplication.enabled and retained_chunk_id is not None:
            disposition = EvidenceSelectionDisposition.duplicate
            duplicate_count += 1
        elif len(selected) == policy.top_k:
            disposition = EvidenceSelectionDisposition.result_limit
            retained_chunk_id = None
            result_limit_count += 1
        elif policy.diversity.enabled and source_counts.get(item.source_id, 0) >= (
            policy.diversity.maximum_per_source
        ):
            disposition = EvidenceSelectionDisposition.source_limit
            retained_chunk_id = None
            diversity_count += 1
        elif policy.diversity.enabled and section_counts.get(item.section_id, 0) >= (
            policy.diversity.maximum_per_section
        ):
            disposition = EvidenceSelectionDisposition.section_limit
            retained_chunk_id = None
            diversity_count += 1
        else:
            disposition = EvidenceSelectionDisposition.selected
            selected.append(hit)
            output_rank = len(selected)
            retained_chunk_id = hit.chunk_id
            retained_by_lineage.setdefault(lineage_value, hit.chunk_id)
            source_counts[item.source_id] = source_counts.get(item.source_id, 0) + 1
            section_counts[item.section_id] = section_counts.get(item.section_id, 0) + 1
        if disposition is not EvidenceSelectionDisposition.selected:
            excluded_score += hit.fused_score
        decisions.append(
            EvidenceSelectionDecision(
                input_rank=hit.rank,
                output_rank=output_rank,
                chunk_id=hit.chunk_id,
                fused_score=hit.fused_score,
                disposition=disposition,
                lineage_value=lineage_value,
                retained_chunk_id=retained_chunk_id,
            )
        )

    return EvidenceSelectionBatch(
        schema_version="bijux.canon.retrieval.evidence_selection.v1",
        generation_id=fusion.generation_id,
        query_text_sha256=fusion.query_text_sha256,
        policy_sha256=_sha256_json(asdict(policy)),
        input_ranking_sha256=_sha256_json(
            [{"artifact_id": hit.artifact_id, "rank": hit.rank} for hit in fusion.hits]
        ),
        candidates=tuple(selected),
        decisions=tuple(decisions),
        duplicate_count=duplicate_count,
        diversity_excluded_count=diversity_count,
        result_limit_excluded_count=result_limit_count,
        excluded_fused_score=excluded_score,
    )


__all__ = [
    "DeduplicationKey",
    "EvidenceDeduplicationPolicy",
    "EvidenceDiversityPolicy",
    "EvidenceLineage",
    "EvidenceSelectionBatch",
    "EvidenceSelectionDecision",
    "EvidenceSelectionDisposition",
    "EvidenceSelectionPolicy",
    "select_evidence",
]
