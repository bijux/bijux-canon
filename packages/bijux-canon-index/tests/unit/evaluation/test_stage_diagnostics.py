# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_index.evaluation.stage_diagnostics import (
    ObservedStageCandidate,
    RelevantEvidenceDisposition,
    RetrievalDiagnosticError,
    RetrievalStage,
    RetrievalStageEvidence,
    aggregate_stage_analysis,
    analyze_query_stages,
)


def _candidate(
    stage: RetrievalStage,
    chunk_id: str,
    rank: int,
    *,
    output_rank: int | None = None,
) -> ObservedStageCandidate:
    return ObservedStageCandidate(
        stage=stage,
        chunk_id=chunk_id,
        source_rank=rank,
        output_rank=rank if output_rank is None else output_rank,
        score=1.0 / rank,
        disposition="included",
    )


def test_stage_analysis_classifies_each_first_loss_without_hiding_qrels() -> None:
    lexical = (
        _candidate(RetrievalStage.lexical, "retained", 1),
        _candidate(RetrievalStage.lexical, "below", 2),
        _candidate(RetrievalStage.lexical, "fusion-loss", 3),
        _candidate(RetrievalStage.lexical, "final-loss", 4),
        ObservedStageCandidate(
            stage=RetrievalStage.lexical,
            chunk_id="channel-limit",
            source_rank=5,
            output_rank=None,
            score=0.1,
            disposition="excluded_by_limit",
        ),
    )
    stages = RetrievalStageEvidence(
        lexical_outcome="success",
        dense_outcome="no_matches",
        fusion_policy_sha256="a" * 64,
        rerank_policy_sha256="b" * 64,
        lexical_candidates=lexical,
        dense_candidates=(),
        fusion_candidates=(
            _candidate(RetrievalStage.fusion, "retained", 1),
            _candidate(RetrievalStage.fusion, "below", 2),
            _candidate(RetrievalStage.fusion, "final-loss", 3),
        ),
        rerank_candidates=(
            _candidate(RetrievalStage.rerank, "retained", 1),
            _candidate(RetrievalStage.rerank, "below", 2),
            _candidate(RetrievalStage.rerank, "final-loss", 3),
        ),
    )
    qrels = tuple(
        (f"qrel-{chunk_id}", chunk_id, 3)
        for chunk_id in (
            "retained",
            "below",
            "absent",
            "channel-limit",
            "fusion-loss",
            "final-loss",
        )
    )

    query = analyze_query_stages(
        query_id="question",
        qrels=qrels,
        status="success",
        stages=stages,
        final_ranks=(("retained", 1), ("below", 11)),
    )

    assert {item.chunk_id: item.disposition for item in query.relevant_evidence} == {
        "retained": RelevantEvidenceDisposition.retained_at_5,
        "below": RelevantEvidenceDisposition.final_below_5,
        "absent": RelevantEvidenceDisposition.absent_from_candidate_depth,
        "channel-limit": RelevantEvidenceDisposition.excluded_by_channel_limit,
        "fusion-loss": RelevantEvidenceDisposition.lost_at_fusion_limit,
        "final-loss": RelevantEvidenceDisposition.lost_at_finalization,
    }
    report = aggregate_stage_analysis((query,))
    assert report.query_count == 1
    assert report.qrel_count == 6
    assert sum(dict(report.disposition_counts).values()) == 6
    assert tuple((item.stage_id, item.numerator) for item in report.recall) == (
        ("candidate-depth", 5),
        ("channel-admitted", 4),
        ("fusion-at-10", 3),
        ("rerank-at-10", 3),
        ("final-at-10", 1),
        ("final-at-5", 1),
    )


def test_stage_analysis_rejects_candidates_invented_by_fusion() -> None:
    stages = RetrievalStageEvidence(
        lexical_outcome="no_matches",
        dense_outcome="no_matches",
        fusion_policy_sha256="a" * 64,
        rerank_policy_sha256="b" * 64,
        lexical_candidates=(),
        dense_candidates=(),
        fusion_candidates=(_candidate(RetrievalStage.fusion, "invented", 1),),
        rerank_candidates=(),
    )

    with pytest.raises(RetrievalDiagnosticError, match="absent from both"):
        analyze_query_stages(
            query_id="question",
            qrels=(("qrel", "invented", 3),),
            status="success",
            stages=stages,
            final_ranks=(("invented", 1),),
        )


@pytest.mark.parametrize(
    ("status", "disposition"),
    [
        ("refused", RelevantEvidenceDisposition.execution_refused),
        ("failed", RelevantEvidenceDisposition.execution_failed),
    ],
)
def test_stage_analysis_keeps_refused_and_failed_qrels(
    status: str,
    disposition: RelevantEvidenceDisposition,
) -> None:
    query = analyze_query_stages(
        query_id="question",
        qrels=(("qrel", "chunk", 3),),
        status=status,
        stages=None,
        final_ranks=(),
    )

    assert query.relevant_evidence[0].disposition is disposition
