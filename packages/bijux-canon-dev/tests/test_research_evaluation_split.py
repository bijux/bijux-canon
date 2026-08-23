"""Coverage, balance, overlap disclosure, and identity checks for the split."""

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
from bijux_canon_dev.corpus.research_claim_truth import load_claim_truth
from bijux_canon_dev.corpus.research_qrels import load_qrels

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"
LOCATOR_TRUTH_PATH = RESEARCH_ROOT / "truth/locator-truth.jsonl"
QRELS_PATH = RESEARCH_ROOT / "truth/qrels.jsonl"
CLAIM_TRUTH_PATH = RESEARCH_ROOT / "truth/claim-truth.jsonl"
SPLIT_PATH = RESEARCH_ROOT / "truth/split.json"


def _document() -> dict[str, object]:
    return load_split(SPLIT_PATH)


def _validate(document: dict[str, object]) -> dict[str, object]:
    return validate_split(
        document,
        claim_truth_path=CLAIM_TRUTH_PATH,
        lock_path=LOCK_PATH,
        locator_truth_path=LOCATOR_TRUTH_PATH,
        qrels_path=QRELS_PATH,
        research_root=RESEARCH_ROOT,
        split_path=SPLIT_PATH,
    )


def _reidentify(document: dict[str, object], case: dict[str, object]) -> None:
    case["case_identity_sha256"] = case_identity(case)
    document["case_set_sha256"] = sha256(canonical(document["cases"]))
    document["split_identity_sha256"] = split_identity(document)


def test_split_freezes_exactly_120_balanced_reviewed_cases() -> None:
    document = _document()
    result = _validate(document)
    assert result["case_count"] == 120
    assert result["development_case_count"] == 80
    assert result["heldout_case_count"] == 40
    assert result["source_count"] == 8


def test_split_reports_semantic_denominators_and_known_leakage() -> None:
    result = _validate(_document())

    assert result["case_row_count"] == 120
    assert result["query_count"] == 8
    assert result["qrel_count"] == 30
    assert result["claim_truth_count"] == 32
    assert result["development_query_count"] == 8
    assert result["heldout_query_count"] == 8
    assert result["query_overlap_count"] == 8
    assert result["qrel_overlap_count"] == 27
    assert result["claim_truth_overlap_count"] == 32
    assert result["leakage_free"] is False


def test_split_validation_is_restart_stable() -> None:
    assert _validate(_document()) == _validate(load_split(SPLIT_PATH))


def test_evaluation_cases_jsonl_is_exact_canonical_split_projection(
    tmp_path: Path,
) -> None:
    output = tmp_path / "evaluation-cases.jsonl"

    write_evaluation_cases(
        _document(),
        output,
        qrels=tuple(load_qrels(QRELS_PATH)),
        claims=tuple(load_claim_truth(CLAIM_TRUTH_PATH)),
    )

    assert (
        output.read_bytes()
        == (RESEARCH_ROOT / "truth/evaluation-cases.jsonl").read_bytes()
    )
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == 120
    assert [item["case_id"] for item in records] == [
        f"adna-case-{ordinal:03d}" for ordinal in range(1, 121)
    ]
    assert all(item["question"].strip() for item in records)
    assert all(item["corpus_scope"]["source_ids"] for item in records)
    assert all(item["filters"]["source_id"] == item["source_id"] for item in records)
    assert {item["answerability"] for item in records} == {
        "answerable",
        "must-abstain",
    }
    assert all(item["rationale"].startswith("Retrieval:") for item in records)
    assert all(item["system_output_consulted"] is False for item in records)
    negative = [item for item in records if item["labels"]["negative"]]
    nonnegative = [item for item in records if not item["labels"]["negative"]]
    assert negative and nonnegative
    assert all(
        item["qrel_disposition"] == "explicit-empty-negative" for item in negative
    )
    assert all(item["qrels"] == [] for item in negative)
    assert all(item["qrel_disposition"] == "reviewed" for item in nonnegative)
    assert all(len(item["qrels"]) == 1 for item in nonnegative)
    for item in nonnegative:
        locator = item["qrels"][0]["locator"]
        assert locator["character_end"] - locator["character_start"] == len(
            locator["exact_text"]
        )
        assert sha256(locator["exact_text"].encode()) == locator["exact_text_sha256"]
        assert item["qrels"][0]["adjudication"]["system_ranking_consulted"] is False
    assert {item["claim_truth"]["claim_class"] for item in records} == {
        "expected",
        "optional",
        "opposed",
        "forbidden",
    }
    for item in records:
        truth = item["claim_truth"]
        citation = truth["citation"]
        assert truth["claim_truth_id"] == item["claim_truth_id"]
        assert citation["character_end"] > citation["character_start"]
        assert sha256(citation["exact_text"].encode()) == citation["exact_text_sha256"]
        assert (
            item["conflict_expectation"]["conflict_expected"]
            == item["labels"]["conflict"]
        )
        assert (
            item["abstention_expectation"]["abstention_expected"]
            == item["labels"]["abstention_expected"]
        )


def test_heldout_labels_cannot_be_enabled_for_tuning() -> None:
    document = deepcopy(_document())
    policy = document["partition_policy"]
    assert isinstance(policy, dict)
    policy["heldout_labels_available_to_tuning"] = True
    document["split_identity_sha256"] = split_identity(document)
    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(document)


def test_case_label_tampering_is_rejected() -> None:
    document = deepcopy(_document())
    cases = document["cases"]
    assert isinstance(cases, list) and isinstance(cases[0], dict)
    labels = cases[0]["labels"]
    assert isinstance(labels, dict)
    labels["relevance_grade"] = 0
    _reidentify(document, cases[0])
    with pytest.raises(RuntimeError, match="case drift"):
        _validate(document)


def test_duplicate_truth_pair_is_rejected() -> None:
    document = deepcopy(_document())
    cases = document["cases"]
    assert isinstance(cases, list)
    first = cases[0]
    second = cases[1]
    assert isinstance(first, dict) and isinstance(second, dict)
    second["qrel_id"] = first["qrel_id"]
    second["claim_truth_id"] = first["claim_truth_id"]
    _reidentify(document, second)
    with pytest.raises(RuntimeError, match="duplicate research evaluation truth pair"):
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
