"""Tests for source-first semantic question-claim evidence truth."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.acquisition import canonical
from bijux_canon_dev.corpus.research_question_claim_truth import (
    load_question_claim_truth,
    validate_question_claim_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_question_claim_truth(
        records,
        cases_path=TRUTH_ROOT / "evaluation-cases.jsonl",
        questions_path=TRUTH_ROOT / "research-questions.jsonl",
        qrels_path=TRUTH_ROOT / "qrels.jsonl",
    )


def test_reviewed_development_points_have_exact_claim_evidence_crosswalk() -> None:
    result = _validate(
        load_question_claim_truth(TRUTH_ROOT / "question-claim-truth.jsonl")
    )

    assert result == {
        "case_count": 12,
        "citation_relation_count": 48,
        "claim_count": 31,
        "question_claim_set_sha256": (
            "26182ecf3aee17f4582e8af8eaa230cf33a10798a6c08f23bdf22061dc9edc04"
        ),
        "reviewer_id": "bijux-production-source-review",
    }


def test_system_output_cannot_define_question_claim_truth() -> None:
    records = load_question_claim_truth(TRUTH_ROOT / "question-claim-truth.jsonl")
    records[0]["system_output_consulted"] = True

    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(records)


def test_answer_point_or_qrel_drift_is_rejected() -> None:
    records = load_question_claim_truth(TRUTH_ROOT / "question-claim-truth.jsonl")
    changed = json.loads(canonical(records[0]).decode("utf-8"))
    changed["claims"][0]["statement"] = "A system-generated replacement point."
    records[0] = changed

    with pytest.raises(RuntimeError, match="differ from reviewed points"):
        _validate(records)

    records = load_question_claim_truth(TRUTH_ROOT / "question-claim-truth.jsonl")
    records[0]["claims"][0]["citations"][0]["qrel_id"] = "unknown-qrel"
    with pytest.raises(RuntimeError, match="invalid question-claim citation"):
        _validate(records)
