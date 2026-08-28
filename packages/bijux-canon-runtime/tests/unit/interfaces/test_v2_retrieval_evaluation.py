# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Transport parity for truth-only installed retrieval evaluation."""

from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from bijux_canon_index.evaluation import (
    ObservedLocatorSegment,
    ObservedRetrievalHit,
    ObservedStageCandidate,
    PublicRetrievalEvaluationRequest,
    PublicRetrievalEvaluator,
    RetrievalExecutionObservation,
    RetrievalExecutionStatus,
    RetrievalStage,
    RetrievalStageEvidence,
    ReviewedRetrievalQuery,
)
from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.operations import RuntimeApplicationServicesV2
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import run_v2_command
from bijux_canon_runtime.runtime.execution.durable_jobs import DurableJobManager
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector

REPO_ROOT = Path(__file__).resolve().parents[5]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"
INDEX_ID = "sha256:" + "a" * 64


def _observation(
    _request: PublicRetrievalEvaluationRequest,
    query: ReviewedRetrievalQuery,
) -> RetrievalExecutionObservation:
    hits = tuple(
        ObservedRetrievalHit(
            rank=rank,
            retrieval_rank=rank,
            score=1.0 / rank,
            chunk_id=qrel.chunk_id,
            document_id=f"document-{rank}",
            source_content_sha256=f"{rank:064x}",
            content_sha256=f"{rank + 100:064x}",
            locator_segments=(
                ObservedLocatorSegment(
                    ordinal=0,
                    mapping_id="sha256:" + f"{rank + 200:064x}",
                    scheme="jats-element-path",
                    selectors=(("element_path", f"/article[1]/body[1]/p[{rank}]"),),
                    content_sha256=f"{rank + 100:064x}",
                ),
            ),
        )
        for rank, qrel in enumerate(query.qrels, 1)
    )
    stage_candidates = tuple(
        ObservedStageCandidate(
            stage=stage,
            chunk_id=qrel.chunk_id,
            source_rank=rank,
            output_rank=rank,
            score=1.0 / rank,
            disposition="included",
        )
        for stage in RetrievalStage
        for rank, qrel in enumerate(query.qrels, 1)
    )
    return RetrievalExecutionObservation(
        query_id=query.query_id,
        query_text_sha256=hashlib.sha256(query.query_text.encode("utf-8")).hexdigest(),
        status=RetrievalExecutionStatus.success,
        generation_id="sha256:" + "b" * 64,
        model_lock_artifact_id="sha256:" + "c" * 64,
        configuration_id="sha256:" + "d" * 64,
        retrieval_mode="local-hybrid-ann",
        hits=hits,
        run_id=f"run-{query.query_id}",
        attempt_id=f"attempt-{query.query_id}",
        vex_artifact_id="sha256:" + "e" * 64,
        policy_action="admitted",
        fallback_action="none",
        stages=RetrievalStageEvidence(
            lexical_outcome="success",
            dense_outcome="success",
            fusion_policy_sha256="f" * 64,
            rerank_policy_sha256="0" * 64,
            lexical_candidates=tuple(
                item
                for item in stage_candidates
                if item.stage is RetrievalStage.lexical
            ),
            dense_candidates=tuple(
                item for item in stage_candidates if item.stage is RetrievalStage.dense
            ),
            fusion_candidates=tuple(
                item for item in stage_candidates if item.stage is RetrievalStage.fusion
            ),
            rerank_candidates=tuple(
                item for item in stage_candidates if item.stage is RetrievalStage.rerank
            ),
        ),
        failure=None,
    )


def _services() -> RuntimeApplicationServicesV2:
    return RuntimeApplicationServicesV2(
        jobs=cast(DurableJobManager, object()),
        inspector=cast(RuntimeRunInspector, object()),
        retrieval_evaluator=PublicRetrievalEvaluator(_observation).evaluate,
    )


def test_cli_and_http_execute_the_same_truth_only_evaluation() -> None:
    services = _services()
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "v2",
            "evaluate-retrieval",
            "--cases",
            str(TRUTH_ROOT / "evaluation-cases.jsonl"),
            "--qrels",
            str(TRUTH_ROOT / "qrels.jsonl"),
            "--index-id",
            INDEX_ID,
        ]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert run_v2_command(args, services=services) == 0
    cli_payload = json.loads(stdout.getvalue())

    response = TestClient(create_app(services)).post(
        "/api/v2/retrieval-evaluations",
        headers={"Bijux-API-Version": "v2"},
        json={
            "cases_path": str(TRUTH_ROOT / "evaluation-cases.jsonl"),
            "qrels_path": str(TRUTH_ROOT / "qrels.jsonl"),
            "index_id": INDEX_ID,
        },
    )

    assert response.status_code == 200
    assert response.json() == cli_payload
    assert cli_payload["query_count"] == 12
    assert cli_payload["qrel_count"] == 29
    assert cli_payload["macro"]["metrics"][0]["denominator"] == 12
    assert not hasattr(args, "hits")


def test_human_summary_discloses_denominators_and_worst_queries() -> None:
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "v2",
            "evaluate-retrieval",
            "--cases",
            str(TRUTH_ROOT / "evaluation-cases.jsonl"),
            "--qrels",
            str(TRUTH_ROOT / "qrels.jsonl"),
            "--index-id",
            INDEX_ID,
            "--human",
        ]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert run_v2_command(args, services=_services()) == 0

    output = stdout.getvalue()
    assert "Queries: 12" in output
    assert "Reviewed qrels: 29" in output
    assert "Macro metrics: Recall@5=" in output
    assert "Relevant-evidence outcomes: retained_at_5=29" in output
    assert "Stage recall: candidate-depth=29/29 (1.000000)" in output
    assert "Stage adna-ambiguous-damage-authentication:" in output
    assert "Worst queries:" in output


def test_configuration_search_cli_retains_development_denominators() -> None:
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "v2",
            "search-retrieval-configurations",
            "--cases",
            str(TRUTH_ROOT / "evaluation-cases.jsonl"),
            "--qrels",
            str(TRUTH_ROOT / "qrels.jsonl"),
            "--index-id",
            INDEX_ID,
        ]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert run_v2_command(args, services=_services()) == 0

    payload = json.loads(stdout.getvalue())
    assert payload["schema_version"] == ("bijux.canon.index.retrieval-config-search.v1")
    assert payload["split"] == "development"
    assert payload["query_count"] == 12
    assert payload["qrel_count"] == 29
    assert payload["selected_configuration_id"] is not None
    assert payload["results"]
