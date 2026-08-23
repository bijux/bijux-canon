"""Diversity, review, and evidence checks for semantic research questions."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.research_questions import (
    CATEGORIES,
    load_questions,
    validate_questions,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUTH_ROOT = REPO_ROOT / "examples/ancient-dna-research/truth"
QUESTIONS_PATH = TRUTH_ROOT / "research-questions.jsonl"
QRELS_PATH = TRUTH_ROOT / "qrels.jsonl"


def _records() -> list[dict[str, object]]:
    return load_questions(QUESTIONS_PATH)


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_questions(records, qrels_path=QRELS_PATH)


def test_questions_cover_diverse_semantic_needs_and_all_sources() -> None:
    result = _validate(_records())
    assert result["question_count"] == 18
    assert result["source_count"] == 8
    assert result["category_counts"] == {category: 2 for category in CATEGORIES}
    assert set(result["answerability_counts"]) == {
        "ambiguous",
        "answerable",
        "out-of-scope",
        "qualified",
    }
    assert set(result["evidence_relation_counts"]) == {
        "contextualizes",
        "limits",
        "opposes",
        "supports",
    }
    assert result["evidence_relevance_grade_counts"] == {"1": 10, "2": 8, "3": 25}


def test_question_validation_is_restart_stable() -> None:
    assert _validate(_records()) == _validate(load_questions(QUESTIONS_PATH))


def test_product_output_cannot_define_question_truth() -> None:
    records = deepcopy(_records())
    records[0]["system_output_consulted"] = True
    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(records)


def test_detached_evidence_is_rejected() -> None:
    records = deepcopy(_records())
    evidence = records[0]["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["qrel_id"] = "missing::qrel::00"
    with pytest.raises(RuntimeError, match="invalid question evidence"):
        _validate(records)


def test_paraphrase_templates_are_rejected() -> None:
    records = deepcopy(_records())
    records[1]["question"] = records[0]["question"]
    with pytest.raises(RuntimeError, match="duplicate research question text"):
        _validate(records)


def test_single_source_cross_paper_question_is_rejected() -> None:
    records = deepcopy(_records())
    record = next(item for item in records if item["category"] == "multi-hop")
    evidence = record["evidence"]
    assert isinstance(evidence, list)
    record["evidence"] = [evidence[0]]
    with pytest.raises(RuntimeError, match="requires multiple sources"):
        _validate(records)
