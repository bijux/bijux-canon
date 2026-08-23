"""Authorization and non-disclosure checks for held-out retrieval scoring."""

from __future__ import annotations

from pathlib import Path

import pytest

from bijux_canon_dev.corpus.research_evaluation_split import load_split
from bijux_canon_dev.corpus.research_questions import load_questions
from bijux_canon_dev.corpus.research_release_evaluation import (
    evaluate_heldout_retrieval,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"
QUESTIONS_PATH = TRUTH_ROOT / "research-questions.jsonl"
SPLIT_PATH = TRUTH_ROOT / "split.json"


def _perfect_submission() -> tuple[
    list[dict[str, object]], dict[str, object], list[dict[str, object]]
]:
    document = load_split(SPLIT_PATH)
    questions = load_questions(QUESTIONS_PATH)
    heldout_ids = {
        str(case["question_id"])
        for case in document["cases"]
        if case["split"] == "heldout"
    }
    submissions = [
        {
            "question_id": question["question_id"],
            "retrieved_qrel_ids": [
                item["qrel_id"]
                for item in sorted(
                    question["evidence"],
                    key=lambda item: int(item["relevance_grade"]),
                    reverse=True,
                )
            ],
        }
        for question in questions
        if question["question_id"] in heldout_ids
    ]
    return submissions, document, questions


def test_release_authorization_is_required() -> None:
    submissions, document, questions = _perfect_submission()
    with pytest.raises(RuntimeError, match="release evaluation requires"):
        evaluate_heldout_retrieval(
            submissions,
            authorization=None,
            document=document,
            questions=questions,
        )


def test_release_evaluator_reports_only_aggregate_metrics() -> None:
    submissions, document, questions = _perfect_submission()
    result = evaluate_heldout_retrieval(
        submissions,
        authorization=str(document["split_identity_sha256"]),
        document=document,
        questions=questions,
    )

    assert result["question_count"] == 6
    assert result["macro_recall_at_5"] == 1.0
    assert result["macro_mrr_at_10"] == 1.0
    assert result["macro_ndcg_at_10"] == 1.0
    assert result["minimum_recall_at_5"] == 1.0
    assert not ({"questions", "evidence", "answer_points"} & set(result))


def test_release_evaluator_rejects_missing_or_duplicate_cases() -> None:
    submissions, document, questions = _perfect_submission()
    authorization = str(document["split_identity_sha256"])
    with pytest.raises(RuntimeError, match="population mismatch"):
        evaluate_heldout_retrieval(
            submissions[:-1],
            authorization=authorization,
            document=document,
            questions=questions,
        )
    duplicated = list(submissions)
    duplicated.append(dict(submissions[0]))
    with pytest.raises(RuntimeError, match="invalid held-out"):
        evaluate_heldout_retrieval(
            duplicated,
            authorization=authorization,
            document=document,
            questions=questions,
        )
