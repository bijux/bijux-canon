"""Coverage, lineage, and anti-ranking checks for research qrels."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.research_qrels import (
    load_qrels,
    qrel_identity,
    validate_qrels,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"
LOCATOR_TRUTH_PATH = RESEARCH_ROOT / "truth/locator-truth.jsonl"
QRELS_PATH = RESEARCH_ROOT / "truth/qrels.jsonl"


def _records() -> list[dict[str, object]]:
    return load_qrels(QRELS_PATH)


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_qrels(
        records,
        lock_path=LOCK_PATH,
        locator_truth_path=LOCATOR_TRUTH_PATH,
        research_root=RESEARCH_ROOT,
    )


def _reidentify(record: dict[str, object]) -> None:
    record["qrel_identity_sha256"] = qrel_identity(record)


def test_qrels_cover_every_source_anchor_and_relevance_grade() -> None:
    records = _records()
    result = _validate(records)
    assert result["source_count"] == 8
    assert result["anchor_count"] == 32
    assert result["qrel_count"] == 30
    by_source: dict[str, set[int]] = {}
    for record in records:
        relevance_grade = record["relevance_grade"]
        assert isinstance(relevance_grade, int)
        by_source.setdefault(str(record["source_id"]), set()).add(relevance_grade)
    assert set(map(frozenset, by_source.values())) == {frozenset({1, 2, 3})}


def test_qrels_validation_is_restart_stable() -> None:
    assert _validate(_records()) == _validate(load_qrels(QRELS_PATH))


def test_system_ranking_labels_are_rejected() -> None:
    records = deepcopy(_records())
    records[0]["system_ranking_consulted"] = True
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="metadata drift"):
        _validate(records)


def test_chunk_text_tampering_is_rejected() -> None:
    records = deepcopy(_records())
    chunk = records[0]["chunk"]
    assert isinstance(chunk, dict)
    chunk["normalized_text"] = f"{chunk['normalized_text']} changed"
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="identity drift"):
        _validate(records)


def test_missing_locator_anchor_is_rejected() -> None:
    records = _records()[1:]
    with pytest.raises(RuntimeError, match="anchor coverage mismatch"):
        _validate(records)


def test_grade_drift_is_rejected() -> None:
    records = deepcopy(_records())
    records[0]["relevance_grade"] = 0
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="invalid research qrel judgment"):
        _validate(records)
