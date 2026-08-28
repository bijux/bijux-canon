"""Coverage, resolution, and drift checks for research locator truth."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.research_locator_truth import (
    load_truth,
    truth_identity,
    validate_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = REPO_ROOT / "examples/ancient-dna-research"
LOCK_PATH = RESEARCH_ROOT / "corpus.lock.json"
TRUTH_PATH = RESEARCH_ROOT / "truth/locator-truth.jsonl"


def _records() -> list[dict[str, object]]:
    return load_truth(TRUTH_PATH)


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_truth(
        records,
        lock_path=LOCK_PATH,
        research_root=RESEARCH_ROOT,
    )


def _reidentify(record: dict[str, object]) -> None:
    record["truth_identity_sha256"] = truth_identity(record)


def test_truth_resolves_four_reviewed_roles_for_every_corpus_source() -> None:
    records = _records()
    result = _validate(records)
    assert result["source_count"] == 8
    assert result["record_count"] == 32
    by_source: dict[str, set[str]] = {}
    for record in records:
        by_source.setdefault(str(record["source_id"]), set()).add(
            str(record["block_role"])
        )
    assert set(map(frozenset, by_source.values())) == {
        frozenset(
            {
                "article-title",
                "abstract-paragraph",
                "body-section-heading",
                "body-paragraph",
            }
        )
    }


def test_truth_validation_is_restart_stable() -> None:
    assert _validate(_records()) == _validate(load_truth(TRUTH_PATH))


def test_exact_text_tampering_is_rejected() -> None:
    records = deepcopy(_records())
    records[0]["exact_text"] = f"{records[0]['exact_text']} changed"
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="exact text mismatch"):
        _validate(records)


def test_character_span_drift_is_rejected() -> None:
    records = deepcopy(_records())
    locator = records[0]["locator"]
    assert isinstance(locator, dict)
    locator["character_start"] = 1
    _reidentify(records[0])
    with pytest.raises(RuntimeError, match="exact text mismatch"):
        _validate(records)


def test_missing_role_is_rejected() -> None:
    records = _records()[1:]
    with pytest.raises(RuntimeError, match="role coverage mismatch"):
        _validate(records)
