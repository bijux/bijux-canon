"""Atomicity, citation, class, and abstention checks for claim truth."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.research_claim_truth import (
    claim_identity,
    load_claim_truth,
    validate_claim_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"
LOCATOR_TRUTH_PATH = RESEARCH_ROOT / "truth/locator-truth.jsonl"
QRELS_PATH = RESEARCH_ROOT / "truth/qrels.jsonl"
CLAIM_TRUTH_PATH = RESEARCH_ROOT / "truth/claim-truth.jsonl"


def _records() -> list[dict[str, object]]:
    return load_claim_truth(CLAIM_TRUTH_PATH)


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_claim_truth(
        records,
        claim_truth_path=CLAIM_TRUTH_PATH,
        lock_path=LOCK_PATH,
        locator_truth_path=LOCATOR_TRUTH_PATH,
        qrels_path=QRELS_PATH,
        research_root=RESEARCH_ROOT,
    )


def _reidentify(record: dict[str, object]) -> None:
    record["claim_identity_sha256"] = claim_identity(record)


def test_claim_truth_covers_every_class_for_every_source() -> None:
    records = _records()
    result = _validate(records)
    assert result["source_count"] == 8
    assert result["claim_count"] == 32
    by_source: dict[str, set[str]] = {}
    for record in records:
        by_source.setdefault(str(record["source_id"]), set()).add(
            str(record["claim_class"])
        )
    assert set(map(frozenset, by_source.values())) == {
        frozenset({"expected", "optional", "opposed", "forbidden"})
    }


def test_claim_truth_validation_is_restart_stable() -> None:
    assert _validate(_records()) == _validate(load_claim_truth(CLAIM_TRUTH_PATH))


def test_opposed_claim_without_abstention_is_rejected() -> None:
    records = deepcopy(_records())
    opposed = next(record for record in records if record["claim_class"] == "opposed")
    opposed["abstention_expected"] = False
    _reidentify(opposed)
    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(records)


def test_exact_citation_tampering_is_rejected() -> None:
    records = deepcopy(_records())
    evidence = records[0]["evidence"]
    assert isinstance(evidence, dict)
    evidence["character_start"] = int(evidence["character_start"]) + 1
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="exact evidence mismatch"):
        _validate(records)


def test_qrel_lineage_drift_is_rejected() -> None:
    records = deepcopy(_records())
    evidence = records[0]["evidence"]
    assert isinstance(evidence, dict)
    evidence["chunk_index"] = int(evidence["chunk_index"]) + 1
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="lineage drift"):
        _validate(records)


def test_missing_claim_class_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="class coverage mismatch"):
        _validate(_records()[1:])
