"""Coverage and drift checks for independent parser locator truth."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.parser_locator_truth import (
    load_truth,
    truth_identity,
    validate_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_ROOT = REPO_ROOT / "examples/document-formats"
TRUTH_PATH = PORTFOLIO_ROOT / "locator-truth.jsonl"


def _records() -> list[dict[str, object]]:
    return load_truth(TRUTH_PATH)


def _validate(records: list[dict[str, object]]) -> dict[str, object]:
    return validate_truth(
        records,
        portfolio_path=PORTFOLIO_ROOT / "sources.jsonl",
        output_root=PORTFOLIO_ROOT,
        lock_path=PORTFOLIO_ROOT / "corpus.lock.json",
    )


def _reidentify(record: dict[str, object]) -> None:
    record["truth_identity_sha256"] = truth_identity(record)


def test_real_truth_covers_every_required_source_and_role() -> None:
    records = _records()
    result = _validate(records)
    assert result == {
        "lock_identity_sha256": (
            "9a0b63f5222b44bb571e8c2ed95b0a1b2abb1e508ac0d6e2ff5aae2fba6366c9"
        ),
        "record_count": 34,
        "source_count": 7,
        "truth_set_sha256": (
            "5e53de286b1cb29ff51685fafa406396f8996a8c604b9a3b7d5d98e1e0c1b8ed"
        ),
    }
    assert len({record["truth_id"] for record in records}) == 34


def test_truth_validation_is_restart_stable() -> None:
    records = _records()
    assert _validate(records) == _validate(load_truth(TRUTH_PATH))


def test_exact_text_hash_drift_is_rejected() -> None:
    records = deepcopy(_records())
    record = next(item for item in records if item["format_id"] == "markdown")
    record["exact_text"] = f"{record['exact_text']} changed"
    _reidentify(record)
    with pytest.raises(RuntimeError, match="exact-text hash mismatch"):
        _validate(records)


def test_resolvable_locator_drift_is_rejected() -> None:
    records = deepcopy(_records())
    record = next(
        item
        for item in records
        if item["parser_source_id"] == "parser-text-real"
        and item["block_role"] == "list-item"
    )
    record["locator"] = {"line_end": 74, "line_start": 74}
    _reidentify(record)
    with pytest.raises(RuntimeError, match="does not resolve exact text"):
        _validate(records)


def test_missing_required_semantic_role_is_rejected() -> None:
    records = [
        record
        for record in _records()
        if record["truth_id"] != "parser-docx-real::table-cell"
    ]
    with pytest.raises(RuntimeError, match="role coverage mismatch"):
        _validate(records)


def test_pdf_truth_is_page_and_extractor_bound() -> None:
    records = _records()
    pdf_records = [record for record in records if record["format_id"] == "pdf-digital"]
    assert {record["block_role"] for record in pdf_records} == {
        "title",
        "abstract",
        "section-heading",
        "body-paragraph",
        "reference",
    }
    for record in pdf_records:
        locator = record["locator"]
        assert isinstance(locator, dict)
        assert locator["extractor"] == "pypdf-6.15.0-page-extract-text"


def test_ocr_truth_is_typed_refusal_without_invented_text() -> None:
    record = next(item for item in _records() if item["format_id"] == "ocr-required")
    assert record["expected_outcome"] == "ocr-required"
    assert record["exact_text"] is None
    assert record["exact_text_sha256"] is None
    assert record["locator"] == {
        "height": 3648,
        "unit": "pixel",
        "width": 4886,
        "x": 0,
        "y": 0,
    }
