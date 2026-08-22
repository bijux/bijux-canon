# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
import hashlib

import pytest

from bijux_canon_index.application import (
    CitationChannel,
    CitationChannelProvenance,
    CitationReadyHit,
    CitationResolutionBatch,
    CitationRetrievalMode,
    CitationSourceMetadata,
    ExactSourceLocator,
    MultiQueryOutcome,
    MultiQueryPolicy,
    PlannedSubquery,
    SubqueryDisposition,
    SubqueryOrigin,
    execute_multi_query,
    plan_subqueries,
)

_GENERATION_ID = "sha256:generation"
_MODE = CitationRetrievalMode.local_hybrid_exact


def _hit(
    rank: int,
    chunk_id: str,
    text: str,
    *,
    score: float,
) -> CitationReadyHit:
    content_sha256 = hashlib.sha256(text.encode()).hexdigest()
    return CitationReadyHit(
        artifact_id="sha256:" + hashlib.sha256(chunk_id.encode()).hexdigest(),
        rank=rank,
        retrieval_rank=rank,
        retrieval_score=score,
        rerank_score=None,
        chunk_id=chunk_id,
        document_id="paper-a",
        ordinal=rank - 1,
        source=CitationSourceMetadata(
            "paper-a",
            "https://doi.org/10.0000/example",
            "a" * 64,
            "jats",
            "Evidence paper",
        ),
        section_path=("results",),
        locator=ExactSourceLocator(
            "jats-element-path",
            (("element_path", f"/article/body/p[{rank}]"),),
        ),
        verbatim_text=text,
        content_sha256=content_sha256,
        mapping_ids=(
            "sha256:" + hashlib.sha256((chunk_id + "map").encode()).hexdigest(),
        ),
        parent_chunk_ids=(),
        locator_record_id="sha256:"
        + hashlib.sha256((chunk_id + "locator").encode()).hexdigest(),
        channels=(
            CitationChannelProvenance(
                CitationChannel.lexical,
                rank,
                score,
                "sha256:"
                + hashlib.sha256((chunk_id + "candidate").encode()).hexdigest(),
            ),
        ),
    )


def _batch(
    subquery: PlannedSubquery,
    hits: Iterable[CitationReadyHit],
    *,
    mode: CitationRetrievalMode = _MODE,
) -> CitationResolutionBatch:
    return CitationResolutionBatch(
        "bijux.canon.retrieval.citation_resolution.v1",
        _GENERATION_ID,
        "sha256:snapshot",
        subquery.text_sha256,
        mode,
        "sha256:" + "b" * 64,
        tuple(hits),
    )


def test_plan_is_transparent_deterministic_and_bounds_fanout() -> None:
    policy = MultiQueryPolicy(max_subqueries=3, per_query_top_k=5, top_k=5)

    first = plan_subqueries(
        "ancient DNA",
        policy=policy,
        supplied_subqueries=("ancient DNA contamination", "ancient DNA"),
        generated_facets=("authentication", "preservation"),
    )
    repeated = plan_subqueries(
        "ancient DNA",
        policy=policy,
        supplied_subqueries=("ancient DNA contamination", "ancient DNA"),
        generated_facets=("authentication", "preservation"),
    )

    assert first == repeated
    assert [item.origin for item in first.subqueries] == [
        SubqueryOrigin.original,
        SubqueryOrigin.supplied,
        SubqueryOrigin.generated_facet,
    ]
    assert [item.disposition for item in first.decisions] == [
        SubqueryDisposition.included,
        SubqueryDisposition.included,
        SubqueryDisposition.duplicate,
        SubqueryDisposition.included,
        SubqueryDisposition.fanout_limit,
    ]
    assert (
        first.decisions[2].duplicate_of_subquery_id == first.subqueries[0].subquery_id
    )
    assert "authentication" in first.subqueries[2].derivation


def test_execution_deduplicates_content_and_attributes_every_subquery() -> None:
    policy = MultiQueryPolicy(max_subqueries=2, per_query_top_k=2, top_k=2)
    plan = plan_subqueries(
        "ancient DNA",
        policy=policy,
        supplied_subqueries=("ancient DNA contamination",),
    )
    calls: list[tuple[str, int]] = []

    def execute(subquery: PlannedSubquery, top_k: int) -> CitationResolutionBatch:
        calls.append((subquery.subquery_id, top_k))
        if subquery.ordinal == 1:
            return _batch(
                subquery,
                (
                    _hit(1, "chunk-a", "shared evidence", score=0.9),
                    _hit(2, "chunk-b", "preservation", score=0.8),
                ),
            )
        return _batch(
            subquery,
            (
                _hit(1, "chunk-c", "contamination", score=0.95),
                _hit(2, "chunk-a-copy", "shared evidence", score=0.7),
            ),
        )

    batch = execute_multi_query(
        plan,
        generation_id=_GENERATION_ID,
        retrieval_mode=_MODE,
        policy=policy,
        executor=execute,
    )

    assert batch.outcome is MultiQueryOutcome.success
    assert calls == [(item.subquery_id, 2) for item in plan.subqueries]
    assert batch.executed_subquery_count == 2
    assert batch.raw_hit_count == 4
    assert batch.deduplicated_hit_count == 3
    assert batch.result_limit_excluded_count == 1
    assert [hit.rank for hit in batch.hits] == [1, 2]
    shared = next(
        hit
        for hit in batch.hits
        if hit.content_sha256 == hashlib.sha256(b"shared evidence").hexdigest()
    )
    assert len(shared.attributions) == 2
    assert {item.subquery_id for item in shared.attributions} == {
        item.subquery_id for item in plan.subqueries
    }
    assert shared.retained_chunk_id == "chunk-a"
    assert shared.duplicate_chunk_ids == ("chunk-a-copy",)


def test_execution_returns_typed_no_matches_without_fabrication() -> None:
    policy = MultiQueryPolicy(max_subqueries=1, per_query_top_k=2, top_k=2)
    plan = plan_subqueries("no evidence", policy=policy)

    batch = execute_multi_query(
        plan,
        generation_id=_GENERATION_ID,
        retrieval_mode=_MODE,
        policy=policy,
        executor=lambda subquery, _top_k: _batch(subquery, ()),
    )

    assert batch.outcome is MultiQueryOutcome.no_matches
    assert batch.raw_hit_count == 0
    assert batch.hits == ()


def test_execution_refuses_policy_result_identity_mode_and_size_drift() -> None:
    policy = MultiQueryPolicy(max_subqueries=1, per_query_top_k=1, top_k=1)
    plan = plan_subqueries("ancient DNA", policy=policy)

    with pytest.raises(ValueError, match="policies differ"):
        execute_multi_query(
            plan,
            generation_id=_GENERATION_ID,
            retrieval_mode=_MODE,
            policy=replace(policy, top_k=2),
            executor=lambda subquery, _top_k: _batch(subquery, ()),
        )
    with pytest.raises(ValueError, match="query identity"):
        execute_multi_query(
            plan,
            generation_id=_GENERATION_ID,
            retrieval_mode=_MODE,
            policy=policy,
            executor=lambda subquery, _top_k: replace(
                _batch(subquery, ()), query_text_sha256="0" * 64
            ),
        )
    with pytest.raises(ValueError, match="mode differs"):
        execute_multi_query(
            plan,
            generation_id=_GENERATION_ID,
            retrieval_mode=_MODE,
            policy=policy,
            executor=lambda subquery, _top_k: _batch(
                subquery, (), mode=CitationRetrievalMode.local_hybrid_ann
            ),
        )
    with pytest.raises(ValueError, match="per-query bound"):
        execute_multi_query(
            plan,
            generation_id=_GENERATION_ID,
            retrieval_mode=_MODE,
            policy=policy,
            executor=lambda subquery, _top_k: _batch(
                subquery,
                (
                    _hit(1, "a", "a", score=1.0),
                    _hit(2, "b", "b", score=0.5),
                ),
            ),
        )


def test_multi_query_policy_and_text_bounds_are_enforced() -> None:
    with pytest.raises(ValueError, match="fan-out"):
        MultiQueryPolicy(0, 1, 1)
    with pytest.raises(ValueError, match="original query"):
        plan_subqueries(" ", policy=MultiQueryPolicy(1, 1, 1))
    with pytest.raises(ValueError, match="text bound"):
        plan_subqueries(
            "long query",
            policy=MultiQueryPolicy(1, 1, 1, max_query_characters=3),
        )
