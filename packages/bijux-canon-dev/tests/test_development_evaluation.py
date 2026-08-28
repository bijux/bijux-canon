"""Tests for persisted-run development evaluation consolidation."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import TypedDict

import pytest

from bijux_canon_dev.quality import (
    DevelopmentEvaluationError,
    build_development_evaluation,
)


class _Inputs(TypedDict):
    source_commit: str
    cases: tuple[Mapping[str, object], ...]
    retrieval: Mapping[str, object]
    outputs: tuple[Mapping[str, object], ...]
    research: Mapping[str, object]
    output_directory: Path
    command: str


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def _case(case_id: str, query_id: str, disposition: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "question_id": query_id,
        "split": "development",
        "system_output_consulted": False,
        "system_output_may_define_truth": False,
        "truth": {
            "abstention_expected": disposition == "abstain",
            "expected_disposition": disposition,
        },
    }


def _output(case_id: str, ordinal: int, disposition: str) -> dict[str, object]:
    answered = disposition == "answered"
    return {
        "schema_version": "bijux.canon.evaluation.system-output.v1",
        "output_id": f"sha256:{ordinal:064x}",
        "case_id": case_id,
        "runtime_run_id": f"run_v1_{ordinal:064x}",
        "runtime_attempt_id": f"attempt_v1_{ordinal + 10:064x}",
        "answer": "answer" if answered else "",
        "disposition": disposition,
        "claims": (
            [{"disposition": "asserted", "claim_id": f"claim-{ordinal}"}]
            if answered
            else []
        ),
        "citations": ([{"citation_id": f"citation-{ordinal}"}] if answered else []),
        "trace_identity_sha256": f"{ordinal + 20:064x}",
        "system_output_may_define_truth": False,
    }


def _retrieval() -> dict[str, object]:
    queries = []
    observations = []
    for ordinal, query_id in enumerate(("query-a", "query-b"), 1):
        chunk_id = f"sha256:{ordinal + 30:064x}"
        queries.append(
            {
                "query_id": query_id,
                "ordered_evidence_ids": [chunk_id],
                "recall_at_5": 1.0,
                "reciprocal_rank_at_10": 1.0,
                "ndcg_at_10": 1.0,
            }
        )
        observations.append(
            {
                "query_id": query_id,
                "run_id": f"run_v1_{ordinal + 40:064x}",
                "attempt_id": f"attempt_v1_{ordinal + 50:064x}",
                "status": "success",
                "hits": [{"chunk_id": chunk_id}],
            }
        )
    metrics = [
        {
            "metric_id": metric_id,
            "value": 1.0,
            "confidence_interval": {
                "lower": 1.0,
                "upper": 1.0,
                "method": "complete fixture population",
            },
        }
        for metric_id in ("recall-at-5", "mrr-at-10", "ndcg-at-10")
    ]
    report: dict[str, object] = {
        "schema_version": "bijux.canon.index.public-retrieval-evaluation.v2",
        "request_sha256": "1" * 64,
        "query_count": 2,
        "qrel_count": 2,
        "generation_ids": ["sha256:" + "2" * 64],
        "model_lock_artifact_ids": ["sha256:" + "3" * 64],
        "configuration_ids": ["sha256:" + "4" * 64],
        "observations": observations,
        "macro": {"queries": queries, "metrics": metrics},
        "micro": {},
        "stage_analysis": {},
        "worst_query_ids": ["query-a"],
    }
    report["evidence_sha256"] = _digest(report)
    return report


def _research() -> dict[str, object]:
    return {
        "case_id": "case-a",
        "run_id": "run_v1_" + "6" * 64,
        "attempt_id": "attempt_v1_" + "7" * 64,
        "trace_artifact_id": "sha256:" + "8" * 64,
        "system_output_may_define_truth": False,
        "budget_usage": {"iterations": 2, "tool_calls": 3},
        "budget_limits": {"iterations": 4, "tool_calls": 5},
        "terminal_outcome": "complete",
    }


def _inputs(tmp_path: Path) -> _Inputs:
    return {
        "source_commit": "9" * 40,
        "cases": (
            _case("case-a", "query-a", "answer"),
            _case("case-b", "query-b", "abstain"),
        ),
        "retrieval": _retrieval(),
        "outputs": (
            _output("case-a", 1, "answered"),
            _output("case-b", 2, "abstained"),
        ),
        "research": _research(),
        "output_directory": tmp_path,
        "command": "bijux-canon-development-evaluation --source-commit " + "9" * 40,
    }


def test_development_report_binds_runs_and_retains_pending_semantics(
    tmp_path: Path,
) -> None:
    report = build_development_evaluation(**_inputs(tmp_path))

    assert report["retrieval_gate_passed"] is True
    assert report["release_readiness"] == "blocked-independent-review"
    assert report["system_output_may_define_truth"] is False
    assert report["pending_dimensions"] == [
        "citation-quality",
        "claim-faithfulness",
        "qualifier-retention",
        "conflict-retention",
        "research-utility",
    ]
    cases = report["cases"]
    assert isinstance(cases, list)
    assert cases[0]["answer"]["run_id"].startswith("run_v1_")
    assert cases[0]["retrieval"]["attempt_id"].startswith("attempt_v1_")
    assert cases[0]["research_utility"]["status"] == ("pending-independent-review")
    assert cases[1]["research_utility"]["status"] == "not-applicable"
    assert (tmp_path / "development-evaluation.json").is_file()
    assert (tmp_path / "evidence-book" / "evidence-book.json").is_file()
    assert len(tuple((tmp_path / "evidence-book" / "cases").glob("*.json"))) == 2


def test_truth_cannot_supply_a_perfect_ranking(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    cases = deepcopy(inputs["cases"])
    assert isinstance(cases, tuple)
    first = cases[0]
    assert isinstance(first, dict)
    first["retrieved_qrel_ids"] = ["qrel-perfect"]
    inputs["cases"] = cases

    with pytest.raises(DevelopmentEvaluationError, match="supplied retrieval"):
        build_development_evaluation(**inputs)


def test_perfect_metrics_without_persisted_runs_are_rejected(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    retrieval = deepcopy(inputs["retrieval"])
    assert isinstance(retrieval, dict)
    retrieval["observations"] = []
    retrieval.pop("evidence_sha256")
    retrieval["evidence_sha256"] = _digest(retrieval)
    inputs["retrieval"] = retrieval

    with pytest.raises(DevelopmentEvaluationError, match="persisted retrieval runs"):
        build_development_evaluation(**inputs)


@pytest.mark.parametrize(
    "field", ["system_output_consulted", "system_output_may_define_truth"]
)
def test_truth_leakage_is_rejected(tmp_path: Path, field: str) -> None:
    inputs = _inputs(tmp_path)
    cases = deepcopy(inputs["cases"])
    assert isinstance(cases, tuple)
    first = cases[0]
    assert isinstance(first, dict)
    first[field] = True
    inputs["cases"] = cases

    with pytest.raises(DevelopmentEvaluationError, match="independent"):
        build_development_evaluation(**inputs)


def test_tampered_retrieval_report_is_rejected(tmp_path: Path) -> None:
    inputs = _inputs(tmp_path)
    retrieval = deepcopy(inputs["retrieval"])
    assert isinstance(retrieval, dict)
    macro = retrieval["macro"]
    assert isinstance(macro, dict)
    metrics = macro["metrics"]
    assert isinstance(metrics, list)
    metric = metrics[0]
    assert isinstance(metric, dict)
    metric["value"] = 0.0
    inputs["retrieval"] = retrieval

    with pytest.raises(DevelopmentEvaluationError, match="identity mismatch"):
        build_development_evaluation(**inputs)
