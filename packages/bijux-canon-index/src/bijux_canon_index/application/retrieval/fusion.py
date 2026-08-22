# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic weighted reciprocal-rank fusion for retrieval candidates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import math
from typing import Self

from .dense import DenseCandidateBatch, DenseCandidateOutcome
from .lexical import LexicalCandidateBatch, LexicalCandidateOutcome


class RetrievalChannel(StrEnum):
    """Canonical channel order used by hybrid retrieval."""

    lexical = "lexical"
    dense = "dense"


@dataclass(frozen=True, slots=True)
class RankedChannelCandidate:
    """One channel-local candidate normalized for fusion."""

    rank: int
    score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str

    def __post_init__(self) -> None:
        if self.rank <= 0 or self.ordinal < 0:
            raise ValueError("fusion candidates require positive ranks and ordinals")
        if not math.isfinite(self.score):
            raise ValueError("fusion candidate scores must be finite")
        if not self.chunk_id or not self.document_id:
            raise ValueError("fusion candidate identities must not be empty")
        if len(self.source_text_sha256) != 64:
            raise ValueError("fusion candidates require a source text SHA-256")


@dataclass(frozen=True, slots=True)
class FusionChannelRanking:
    """Complete ordered result from one generation-bound channel."""

    generation_id: str
    query_text_sha256: str
    channel: RetrievalChannel
    candidates: tuple[RankedChannelCandidate, ...]

    def __post_init__(self) -> None:
        if not self.generation_id or len(self.query_text_sha256) != 64:
            raise ValueError("fusion ranking identities must be complete")
        if not isinstance(self.channel, RetrievalChannel):
            raise ValueError("fusion ranking channel is unsupported")
        ranks = tuple(candidate.rank for candidate in self.candidates)
        if ranks != tuple(range(1, len(ranks) + 1)):
            raise ValueError("fusion channel ranks must be unique and contiguous")
        chunk_ids = tuple(candidate.chunk_id for candidate in self.candidates)
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("fusion channel chunk identities must be unique")

    @classmethod
    def from_lexical(cls, batch: LexicalCandidateBatch) -> Self:
        """Normalize an admitted or typed-empty lexical batch."""

        if batch.outcome is LexicalCandidateOutcome.empty_query:
            raise ValueError("empty lexical queries cannot enter fusion")
        return cls(
            generation_id=batch.generation_id,
            query_text_sha256=batch.query_text_sha256,
            channel=RetrievalChannel.lexical,
            candidates=tuple(
                RankedChannelCandidate(
                    rank=candidate.output_rank,
                    score=candidate.score,
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    ordinal=candidate.ordinal,
                    source_text_sha256=candidate.source_text_sha256,
                )
                for candidate in batch.candidates
                if candidate.output_rank is not None
            ),
        )

    @classmethod
    def from_dense(cls, batch: DenseCandidateBatch) -> Self:
        """Normalize an admitted or typed-empty dense VEX batch."""

        if batch.outcome is DenseCandidateOutcome.refused:
            raise ValueError("refused dense executions cannot enter fusion")
        return cls(
            generation_id=batch.generation_id,
            query_text_sha256=batch.query_text_sha256,
            channel=RetrievalChannel.dense,
            candidates=tuple(
                RankedChannelCandidate(
                    rank=candidate.source_rank,
                    score=candidate.score,
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    ordinal=candidate.ordinal,
                    source_text_sha256=candidate.source_text_sha256,
                )
                for candidate in batch.candidates
            ),
        )


@dataclass(frozen=True, slots=True)
class RrfFusionPolicy:
    """Frozen weighted-RRF parameters and output bound."""

    rank_constant: int = 60
    lexical_weight: float = 1.0
    dense_weight: float = 1.0
    top_k: int = 10

    def __post_init__(self) -> None:
        if not 1 <= self.rank_constant <= 10_000:
            raise ValueError("RRF rank constant must be within 1..10000")
        if not 1 <= self.top_k <= 1000:
            raise ValueError("RRF top_k must be within 1..1000")
        if any(
            not math.isfinite(weight) or weight <= 0
            for weight in (self.lexical_weight, self.dense_weight)
        ):
            raise ValueError("RRF channel weights must be finite and positive")

    def weight(self, channel: RetrievalChannel) -> float:
        """Return the frozen weight for one channel."""

        return (
            self.lexical_weight
            if channel is RetrievalChannel.lexical
            else self.dense_weight
        )


@dataclass(frozen=True, slots=True)
class RrfContribution:
    """Auditable contribution of one channel rank to a fused score."""

    candidate_artifact_id: str
    channel: RetrievalChannel
    channel_rank: int
    channel_score: float
    channel_weight: float
    weighted_score: float


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    """One stable hybrid result with all channel contributions."""

    artifact_id: str
    rank: int
    fused_score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str
    contributions: tuple[RrfContribution, ...]
    fusion_method: str = "rrf-v1"
    deterministic_tiebreak: str = "fused_score_then_chunk_artifact_id"


@dataclass(frozen=True, slots=True)
class RrfFusionBatch:
    """Content-bound deterministic hybrid ranking."""

    schema_version: str
    generation_id: str
    query_text_sha256: str
    policy_sha256: str
    channel_rankings_sha256: str
    hits: tuple[FusedCandidate, ...]


def _sha256_json(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _candidate_artifact_id(
    ranking: FusionChannelRanking,
    candidate: RankedChannelCandidate,
) -> str:
    return f"sha256:{_sha256_json({'candidate': asdict(candidate), 'channel': ranking.channel.value, 'generation_id': ranking.generation_id, 'query_text_sha256': ranking.query_text_sha256})}"


def reciprocal_rank_fusion(
    rankings: tuple[FusionChannelRanking, ...],
    *,
    policy: RrfFusionPolicy | None = None,
) -> RrfFusionBatch:
    """Fuse exactly one lexical and one dense ranking with stable tie breaks."""

    resolved_policy = policy or RrfFusionPolicy()
    by_channel = {ranking.channel: ranking for ranking in rankings}
    if len(rankings) != 2 or set(by_channel) != set(RetrievalChannel):
        raise ValueError(
            "hybrid RRF requires exactly one lexical and one dense ranking"
        )
    generations = {ranking.generation_id for ranking in rankings}
    query_hashes = {ranking.query_text_sha256 for ranking in rankings}
    if len(generations) != 1:
        raise ValueError("fusion rankings must use the same generation")
    if len(query_hashes) != 1:
        raise ValueError("fusion rankings must use the same query identity")

    accumulated: dict[str, list[tuple[RankedChannelCandidate, RrfContribution]]] = {}
    ranking_payload = []
    for channel in RetrievalChannel:
        ranking = by_channel[channel]
        ranking_payload.append(
            {
                "channel": channel.value,
                "candidates": [asdict(candidate) for candidate in ranking.candidates],
            }
        )
        for candidate in ranking.candidates:
            weighted_score = resolved_policy.weight(channel) / (
                resolved_policy.rank_constant + candidate.rank
            )
            contribution = RrfContribution(
                candidate_artifact_id=_candidate_artifact_id(ranking, candidate),
                channel=channel,
                channel_rank=candidate.rank,
                channel_score=candidate.score,
                channel_weight=resolved_policy.weight(channel),
                weighted_score=weighted_score,
            )
            accumulated.setdefault(candidate.chunk_id, []).append(
                (candidate, contribution)
            )

    fused = []
    for chunk_id, entries in accumulated.items():
        identities = {
            (item.document_id, item.ordinal, item.source_text_sha256)
            for item, _ in entries
        }
        if len(identities) != 1:
            raise ValueError("fusion channels disagree on immutable chunk identity")
        candidate = entries[0][0]
        contributions = tuple(contribution for _, contribution in entries)
        fused_score = sum(item.weighted_score for item in contributions)
        fused.append((fused_score, chunk_id, candidate, contributions))
    fused.sort(key=lambda item: (-item[0], item[1]))

    hits = []
    for rank, (score, chunk_id, candidate, contributions) in enumerate(
        fused[: resolved_policy.top_k], start=1
    ):
        identity = {
            "chunk_id": chunk_id,
            "contributions": [asdict(item) for item in contributions],
            "fused_score": score,
            "generation_id": next(iter(generations)),
            "query_text_sha256": next(iter(query_hashes)),
            "rank": rank,
        }
        hits.append(
            FusedCandidate(
                artifact_id=f"sha256:{_sha256_json(identity)}",
                rank=rank,
                fused_score=score,
                chunk_id=chunk_id,
                document_id=candidate.document_id,
                ordinal=candidate.ordinal,
                source_text_sha256=candidate.source_text_sha256,
                contributions=contributions,
            )
        )
    return RrfFusionBatch(
        schema_version="bijux.canon.retrieval.rrf_fusion.v1",
        generation_id=next(iter(generations)),
        query_text_sha256=next(iter(query_hashes)),
        policy_sha256=_sha256_json(asdict(resolved_policy)),
        channel_rankings_sha256=_sha256_json(ranking_payload),
        hits=tuple(hits),
    )


__all__ = [
    "FusedCandidate",
    "FusionChannelRanking",
    "RankedChannelCandidate",
    "RetrievalChannel",
    "RrfContribution",
    "RrfFusionBatch",
    "RrfFusionPolicy",
    "reciprocal_rank_fusion",
]
