"""Family partition, label sealing, and identity checks for research truth."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_evaluation_split import (
    case_identity,
    load_split,
    split_identity,
    validate_split,
    write_evaluation_cases,
)
from bijux_canon_dev.corpus.research_questions import load_questions

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
TRUTH_ROOT = RESEARCH_ROOT / "truth"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"
LOCATOR_TRUTH_PATH = TRUTH_ROOT / "locator-truth.jsonl"
PARTITION_REVIEW_PATH = TRUTH_ROOT / "question-partition-review.jsonl"
QRELS_PATH = TRUTH_ROOT / "qrels.jsonl"
QUESTIONS_PATH = TRUTH_ROOT / "research-questions.jsonl"
SPLIT_PATH = TRUTH_ROOT / "split.json"


def _document() -> dict[str, object]:
    return load_split(SPLIT_PATH)


def _validate(document: dict[str, object]) -> dict[str, object]:
    return validate_split(
        document,
        lock_path=LOCK_PATH,
        locator_truth_path=LOCATOR_TRUTH_PATH,
        partition_review_path=PARTITION_REVIEW_PATH,
        qrels_path=QRELS_PATH,
        questions_path=QUESTIONS_PATH,
        research_root=RESEARCH_ROOT,
        split_path=SPLIT_PATH,
    )


def _reidentify(document: dict[str, object], case: dict[str, object]) -> None:
    case["case_identity_sha256"] = case_identity(case)
    document["case_set_sha256"] = sha256(canonical(document["cases"]))
    document["split_identity_sha256"] = split_identity(document)


def test_split_freezes_one_case_per_reviewed_semantic_question() -> None:
    result = _validate(_document())

    assert result["case_count"] == 18
    assert result["question_count"] == 18
    assert result["development_case_count"] == 12
    assert result["heldout_case_count"] == 6
    assert result["development_family_count"] == 3
    assert result["heldout_family_count"] == 1
    assert result["heldout_category_count"] == 6


def test_split_is_disjoint_by_question_and_complete_evidence_family() -> None:
    result = _validate(_document())

    assert result["question_overlap_count"] == 0
    assert result["family_overlap_count"] == 0
    assert result["leakage_free"] is True
    assert result["heldout_labels_available_to_tuning"] is False
    assert len(str(result["development_label_set_sha256"])) == 64
    assert len(str(result["heldout_label_set_sha256"])) == 64


def test_split_validation_is_restart_stable() -> None:
    assert _validate(_document()) == _validate(load_split(SPLIT_PATH))


def test_runnable_cases_seal_heldout_truth(tmp_path: Path) -> None:
    output = tmp_path / "evaluation-cases.jsonl"
    write_evaluation_cases(
        _document(),
        output,
        questions=tuple(load_questions(QUESTIONS_PATH)),
    )

    assert output.read_bytes() == (TRUTH_ROOT / "evaluation-cases.jsonl").read_bytes()
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == 18
    development = [record for record in records if record["split"] == "development"]
    heldout = [record for record in records if record["split"] == "heldout"]
    assert len(development) == 12
    assert len(heldout) == 6
    assert all(
        record["label_disposition"] == "development-labels-visible"
        for record in development
    )
    assert all(
        record["label_disposition"] == "heldout-labels-sealed" for record in heldout
    )
    assert all("truth" in record for record in development)
    assert all("truth" not in record for record in heldout)
    assert all(len(record["truth_sha256"]) == 64 for record in records)
    assert all(record["system_output_consulted"] is False for record in records)


def test_heldout_labels_cannot_be_enabled_for_tuning() -> None:
    document = deepcopy(_document())
    policy = document["partition_policy"]
    assert isinstance(policy, dict)
    policy["heldout_labels_available_to_tuning"] = True
    document["split_identity_sha256"] = split_identity(document)
    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(document)


def test_evidence_family_cannot_cross_partitions() -> None:
    document = deepcopy(_document())
    cases = document["cases"]
    assert isinstance(cases, list)
    heldout = next(case for case in cases if case["split"] == "heldout")
    development = next(case for case in cases if case["split"] == "development")
    assert isinstance(heldout, dict) and isinstance(development, dict)
    development["evidence_family"] = heldout["evidence_family"]
    _reidentify(document, development)
    with pytest.raises(RuntimeError, match="case drift|crosses partitions"):
        _validate(document)


def test_question_label_hash_tampering_is_rejected() -> None:
    document = deepcopy(_document())
    cases = document["cases"]
    assert isinstance(cases, list) and isinstance(cases[0], dict)
    cases[0]["question_label_sha256"] = "0" * 64
    _reidentify(document, cases[0])
    with pytest.raises(RuntimeError, match="case drift"):
        _validate(document)


def test_partition_index_drift_is_rejected() -> None:
    document = deepcopy(_document())
    partitions = document["partitions"]
    assert isinstance(partitions, dict)
    development = partitions["development"]
    assert isinstance(development, list)
    development.reverse()
    document["split_identity_sha256"] = split_identity(document)
    with pytest.raises(RuntimeError, match="partition index mismatch"):
        _validate(document)
