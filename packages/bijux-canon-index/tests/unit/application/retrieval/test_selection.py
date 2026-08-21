# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from bijux_canon_index.application import (
    DeduplicationKey,
    EvidenceDeduplicationPolicy,
    EvidenceDiversityPolicy,
    EvidenceLineage,
    EvidenceSelectionDisposition,
    EvidenceSelectionPolicy,
    FusedCandidate,
    RrfFusionBatch,
    select_evidence,
)


def _hit(rank: int, chunk_id: str, score: float) -> FusedCandidate:
    return FusedCandidate(
        artifact_id=f"sha256:{rank:064x}",
        rank=rank,
        fused_score=score,
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        ordinal=0,
        source_text_sha256=f"{rank:064x}",
        contributions=(),
    )


def _fusion() -> RrfFusionBatch:
    return RrfFusionBatch(
        "bijux.canon.retrieval.rrf_fusion.v1",
        "sha256:generation",
        "a" * 64,
        "b" * 64,
        "c" * 64,
        (
            _hit(1, "chunk-a", 0.9),
            _hit(2, "chunk-b", 0.8),
            _hit(3, "chunk-c", 0.7),
            _hit(4, "chunk-d", 0.6),
            _hit(5, "chunk-e", 0.5),
        ),
    )


def _lineage() -> tuple[EvidenceLineage, ...]:
    return (
        EvidenceLineage("chunk-a", "content-a", "span-a", "source-a", "section-a"),
        EvidenceLineage("chunk-b", "content-a", "span-b", "source-b", "section-b"),
        EvidenceLineage("chunk-c", "content-c", "span-c", "source-a", "section-c"),
        EvidenceLineage("chunk-d", "content-d", "span-d", "source-d", "section-a"),
        EvidenceLineage("chunk-e", "content-e", "span-e", "source-e", "section-e"),
    )


def test_selection_deduplicates_then_diversifies_with_full_loss_accounting() -> None:
    policy = EvidenceSelectionPolicy(
        top_k=3,
        deduplication=EvidenceDeduplicationPolicy(
            lineage_key=DeduplicationKey.content_hash
        ),
        diversity=EvidenceDiversityPolicy(
            enabled=True,
            maximum_per_source=1,
            maximum_per_section=1,
        ),
    )

    batch = select_evidence(_fusion(), _lineage(), policy=policy)

    assert [candidate.chunk_id for candidate in batch.candidates] == [
        "chunk-a",
        "chunk-e",
    ]
    assert [decision.disposition for decision in batch.decisions] == [
        EvidenceSelectionDisposition.selected,
        EvidenceSelectionDisposition.duplicate,
        EvidenceSelectionDisposition.source_limit,
        EvidenceSelectionDisposition.section_limit,
        EvidenceSelectionDisposition.selected,
    ]
    assert batch.decisions[1].retained_chunk_id == "chunk-a"
    assert batch.duplicate_count == 1
    assert batch.diversity_excluded_count == 2
    assert batch.result_limit_excluded_count == 0
    assert batch.excluded_fused_score == pytest.approx(2.1)


def test_selection_preserves_best_provenance_and_applies_output_limit() -> None:
    policy = EvidenceSelectionPolicy(
        top_k=2,
        deduplication=EvidenceDeduplicationPolicy(
            lineage_key=DeduplicationKey.source_span
        ),
    )

    first = select_evidence(_fusion(), _lineage(), policy=policy)
    repeated = select_evidence(_fusion(), tuple(reversed(_lineage())), policy=policy)

    assert first == repeated
    assert first.candidates == _fusion().hits[:2]
    assert first.result_limit_excluded_count == 3
    assert [decision.output_rank for decision in first.decisions[:2]] == [1, 2]


def test_selection_refuses_missing_duplicate_and_drifted_lineage() -> None:
    policy = EvidenceSelectionPolicy(top_k=2)

    with pytest.raises(ValueError, match="exactly once"):
        select_evidence(_fusion(), _lineage()[:-1], policy=policy)
    with pytest.raises(ValueError, match="exactly once"):
        select_evidence(_fusion(), _lineage() + (_lineage()[0],), policy=policy)
    with pytest.raises(ValueError, match="contiguous"):
        select_evidence(
            replace(_fusion(), hits=(replace(_fusion().hits[0], rank=2),)),
            (_lineage()[0],),
            policy=policy,
        )


def test_selection_policy_validates_bounds() -> None:
    with pytest.raises(ValueError, match="top_k"):
        EvidenceSelectionPolicy(top_k=0)
    with pytest.raises(ValueError, match="diversity"):
        EvidenceDiversityPolicy(maximum_per_source=0)
