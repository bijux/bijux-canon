"""Coverage, balance, isolation, and identity checks for the research split."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.acquisition import canonical, sha256
from bijux_canon_dev.corpus.research_evaluation_split import (
    case_identity,
    load_split,
    split_identity,
    validate_split,
)


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


def test_split_validation_is_restart_stable() -> None:
    assert _validate(_document()) == _validate(load_split(SPLIT_PATH))


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
