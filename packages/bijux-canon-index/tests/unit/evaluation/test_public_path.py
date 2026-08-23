# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Tests that retrieval evaluation executes instead of accepting ranked hits."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from bijux_canon_index.evaluation import (
    ObservedLocatorSegment,
    ObservedRetrievalHit,
    ObservedStageCandidate,
    PublicRetrievalEvaluationError,
    PublicRetrievalEvaluationRequest,
    PublicRetrievalEvaluator,
    PublicRetrievalMode,
    RetrievalExecutionObservation,
    RetrievalExecutionStatus,
    RetrievalStage,
    RetrievalStageEvidence,
    ReviewedRetrievalQrel,
    ReviewedRetrievalQuery,
    load_reviewed_retrieval_request,
)

REPO_ROOT = Path(__file__).resolve().parents[5]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"
INDEX_ID = "sha256:" + "a" * 64


def _query(query_id: str, chunk_id: str) -> ReviewedRetrievalQuery:
    return ReviewedRetrievalQuery(
        query_id=query_id,
        query_text=f"question for {query_id}",
        input_identity_sha256="b" * 64,
        qrels=(
            ReviewedRetrievalQrel(
                qrel_id=f"{query_id}::qrel",
                chunk_id=chunk_id,
                relevance_grade=3,
                relation="supports",
                qrel_identity_sha256="c" * 64,
            ),
        ),
    )


def _observation(
    query: ReviewedRetrievalQuery,
    *,
    hit: bool,
    status: RetrievalExecutionStatus = RetrievalExecutionStatus.success,
) -> RetrievalExecutionObservation:
    hits = (
        (
            ObservedRetrievalHit(
                rank=1,
                retrieval_rank=1,
                score=0.75,
                chunk_id=query.qrels[0].chunk_id,
                document_id="paper-a",
                source_content_sha256="d" * 64,
                content_sha256="e" * 64,
                locator_segments=(
                    ObservedLocatorSegment(
                        ordinal=0,
                        mapping_id="sha256:" + "f" * 64,
                        scheme="jats-element-path",
                        selectors=(("element_path", "/article[1]/body[1]/p[1]"),),
                        content_sha256="e" * 64,
                    ),
                ),
            ),
        )
        if hit
        else ()
    )
    stages = None
    if status not in {
        RetrievalExecutionStatus.refused,
        RetrievalExecutionStatus.failed,
    }:
        candidates = tuple(
            ObservedStageCandidate(
                stage=stage,
                chunk_id=query.qrels[0].chunk_id,
                source_rank=1,
                output_rank=1,
                score=0.75,
                disposition="included",
            )
            for stage in RetrievalStage
            if hit
        )
        stages = RetrievalStageEvidence(
            lexical_outcome="success" if hit else "no_matches",
            dense_outcome="success" if hit else "no_matches",
            fusion_policy_sha256="9" * 64,
            lexical_candidates=tuple(
                item for item in candidates if item.stage is RetrievalStage.lexical
            ),
            dense_candidates=tuple(
                item for item in candidates if item.stage is RetrievalStage.dense
            ),
            fusion_candidates=tuple(
                item for item in candidates if item.stage is RetrievalStage.fusion
            ),
        )
    return RetrievalExecutionObservation(
        query_id=query.query_id,
        query_text_sha256=__import__("hashlib")
        .sha256(query.query_text.encode("utf-8"))
        .hexdigest(),
        status=status,
        generation_id="sha256:" + "1" * 64,
        model_lock_artifact_id="sha256:" + "2" * 64,
        configuration_id="sha256:" + "3" * 64,
        retrieval_mode="local-hybrid-ann",
        hits=hits,
        run_id=None if status is RetrievalExecutionStatus.refused else "run-a",
        attempt_id=None if status is RetrievalExecutionStatus.refused else "attempt-a",
        vex_artifact_id="sha256:" + "4" * 64,
        policy_action="refuse"
        if status is RetrievalExecutionStatus.refused
        else "admit",
        fallback_action="none",
        stages=stages,
        failure="below VEX policy"
        if status is RetrievalExecutionStatus.refused
        else None,
    )


def test_public_evaluator_executes_every_unique_query_and_keeps_failures() -> None:
    queries = (_query("query-good", "chunk-good"), _query("query-refused", "chunk-r"))
    request = PublicRetrievalEvaluationRequest.create(
        index_artifact_id=INDEX_ID,
        split="development",
        mode=PublicRetrievalMode.hybrid_ann,
        queries=queries,
    )
    executed: list[str] = []

    def execute(
        _request: PublicRetrievalEvaluationRequest, query: ReviewedRetrievalQuery
    ) -> RetrievalExecutionObservation:
        executed.append(query.query_id)
        if query.query_id == "query-refused":
            return _observation(
                query,
                hit=False,
                status=RetrievalExecutionStatus.refused,
            )
        return _observation(query, hit=True)

    report = PublicRetrievalEvaluator(execute).evaluate(request)

    assert executed == ["query-good", "query-refused"]
    assert report.query_count == report.macro.metric("recall-at-5").denominator == 2
    assert report.qrel_count == report.micro.relevant_qrels == 2
    assert report.micro.retrieved_relevant_at_5 == 1
    assert report.micro.recall_at_5 == 0.5
    assert report.micro.refused_queries == 1
    assert dict(report.stage_analysis.disposition_counts) == {
        "execution_refused": 1,
        "retained_at_5": 1,
    }
    assert report.macro.metric("recall-at-5").value == 0.5
    assert report.worst_query_ids[0] == "query-refused"
    assert report.manifest()["evidence_sha256"] == report.evidence_sha256


def test_reviewed_loader_uses_unique_semantic_questions_without_hit_input() -> None:
    request = load_reviewed_retrieval_request(
        cases_path=TRUTH_ROOT / "evaluation-cases.jsonl",
        qrels_path=TRUTH_ROOT / "qrels.jsonl",
        index_artifact_id=INDEX_ID,
    )

    assert request.split == "development"
    assert len(request.queries) == 12
    assert len({query.query_id for query in request.queries}) == 12
    assert sum(len(query.qrels) for query in request.queries) == 29
    assert request.candidate_limit == request.top_k * 4
    assert all(not hasattr(query, "hits") for query in request.queries)
    assert "hits" not in PublicRetrievalEvaluationRequest.__dataclass_fields__


def test_reviewed_loader_rejects_prefilled_hits_and_sealed_labels(
    tmp_path: Path,
) -> None:
    records = [
        json.loads(line)
        for line in (TRUTH_ROOT / "evaluation-cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    records[0]["hits"] = [{"chunk_id": "forbidden"}]
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    with pytest.raises(PublicRetrievalEvaluationError, match="supplied retrieval hits"):
        load_reviewed_retrieval_request(
            cases_path=cases,
            qrels_path=TRUTH_ROOT / "qrels.jsonl",
            index_artifact_id=INDEX_ID,
        )
    with pytest.raises(PublicRetrievalEvaluationError, match="authorized release"):
        load_reviewed_retrieval_request(
            cases_path=TRUTH_ROOT / "evaluation-cases.jsonl",
            qrels_path=TRUTH_ROOT / "qrels.jsonl",
            index_artifact_id=INDEX_ID,
            split="heldout",
        )


def test_public_request_and_observation_fail_closed_on_identity_drift() -> None:
    query = _query("query", "chunk")
    request = PublicRetrievalEvaluationRequest.create(
        index_artifact_id=INDEX_ID,
        split="development",
        mode=PublicRetrievalMode.hybrid_exact,
        queries=(query,),
    )
    with pytest.raises(ValueError, match="request identity mismatch"):
        replace(request, top_k=11)

    wrong = replace(_observation(query, hit=True), query_id="other")
    with pytest.raises(PublicRetrievalEvaluationError, match="query identity"):
        PublicRetrievalEvaluator(lambda _request, _query: wrong).evaluate(request)
