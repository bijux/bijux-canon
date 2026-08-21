# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_index.application import (
    FusionChannelRanking,
    RankedChannelCandidate,
    RetrievalChannel,
    RrfFusionPolicy,
    reciprocal_rank_fusion,
)


def _candidate(rank: int, chunk_id: str, *, score: float = 1.0):
    return RankedChannelCandidate(
        rank=rank,
        score=score,
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        ordinal=0,
        source_text_sha256=(chunk_id[-1] * 64),
    )


def _ranking(
    channel: RetrievalChannel,
    candidates: tuple[RankedChannelCandidate, ...],
) -> FusionChannelRanking:
    return FusionChannelRanking("sha256:generation", "a" * 64, channel, candidates)


def test_weighted_rrf_retains_contributions_and_stable_order() -> None:
    lexical = _ranking(
        RetrievalChannel.lexical,
        (_candidate(1, "chunk-a", score=9.0), _candidate(2, "chunk-b", score=8.0)),
    )
    dense = _ranking(
        RetrievalChannel.dense,
        (_candidate(1, "chunk-b", score=0.9), _candidate(2, "chunk-a", score=0.8)),
    )
    policy = RrfFusionPolicy(
        rank_constant=60, lexical_weight=2.0, dense_weight=1.0, top_k=2
    )

    first = reciprocal_rank_fusion((lexical, dense), policy=policy)
    repeated = reciprocal_rank_fusion((dense, lexical), policy=policy)

    assert first == repeated
    assert [hit.chunk_id for hit in first.hits] == ["chunk-a", "chunk-b"]
    assert first.hits[0].fused_score == pytest.approx(2 / 61 + 1 / 62)
    assert [item.channel for item in first.hits[0].contributions] == [
        RetrievalChannel.lexical,
        RetrievalChannel.dense,
    ]
    assert all(
        item.candidate_artifact_id.startswith("sha256:")
        for item in first.hits[0].contributions
    )
    assert first.policy_sha256 == repeated.policy_sha256
    assert first.channel_rankings_sha256 == repeated.channel_rankings_sha256


def test_rrf_uses_chunk_identity_as_final_tie_break() -> None:
    lexical = _ranking(RetrievalChannel.lexical, (_candidate(1, "chunk-b"),))
    dense = _ranking(RetrievalChannel.dense, (_candidate(1, "chunk-a"),))

    batch = reciprocal_rank_fusion(
        (lexical, dense),
        policy=RrfFusionPolicy(rank_constant=1, top_k=2),
    )

    assert [hit.chunk_id for hit in batch.hits] == ["chunk-a", "chunk-b"]
    assert len({hit.artifact_id for hit in batch.hits}) == 2


def test_rrf_accepts_a_typed_empty_channel_without_fabricating_hits() -> None:
    lexical = _ranking(RetrievalChannel.lexical, ())
    dense = _ranking(RetrievalChannel.dense, (_candidate(1, "chunk-a"),))

    batch = reciprocal_rank_fusion((lexical, dense))

    assert [hit.chunk_id for hit in batch.hits] == ["chunk-a"]
    assert batch.hits[0].contributions[0].channel is RetrievalChannel.dense


@pytest.mark.parametrize(
    "rankings",
    [
        (_ranking(RetrievalChannel.lexical, ()),),
        (
            _ranking(RetrievalChannel.lexical, ()),
            _ranking(RetrievalChannel.lexical, ()),
        ),
    ],
)
def test_rrf_requires_exactly_one_ranking_per_hybrid_channel(rankings) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        reciprocal_rank_fusion(rankings)


def test_rrf_refuses_generation_query_and_chunk_identity_drift() -> None:
    lexical = _ranking(RetrievalChannel.lexical, (_candidate(1, "chunk-a"),))
    dense = _ranking(RetrievalChannel.dense, (_candidate(1, "chunk-a"),))

    with pytest.raises(ValueError, match="same generation"):
        reciprocal_rank_fusion((lexical, replace(dense, generation_id="other")))
    with pytest.raises(ValueError, match="same query"):
        reciprocal_rank_fusion((lexical, replace(dense, query_text_sha256="b" * 64)))
    drifted = replace(
        dense,
        candidates=(replace(dense.candidates[0], document_id="other"),),
    )
    with pytest.raises(ValueError, match="immutable chunk identity"):
        reciprocal_rank_fusion((lexical, drifted))


def test_rrf_validates_channel_ranks_weights_and_bounds() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        _ranking(RetrievalChannel.lexical, (_candidate(2, "chunk-a"),))
    with pytest.raises(ValueError, match="weights"):
        RrfFusionPolicy(lexical_weight=0)
    with pytest.raises(ValueError, match="top_k"):
        RrfFusionPolicy(top_k=0)
