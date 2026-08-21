"""Admission and scope checks for the parser-qualification portfolio."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from bijux_canon_dev.corpus.parser_admission import (
    admission_identity,
    build_admission,
    validate_admission_document,
    write_admission,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_ROOT = REPO_ROOT / "examples/document-formats"
SOURCE_COMMIT = "a" * 40


def _admission() -> dict[str, object]:
    return build_admission(
        source_commit=SOURCE_COMMIT,
        portfolio_path=PORTFOLIO_ROOT / "sources.jsonl",
        output_root=PORTFOLIO_ROOT,
        lock_path=PORTFOLIO_ROOT / "corpus.lock.json",
        truth_path=PORTFOLIO_ROOT / "locator-truth.jsonl",
    )


def test_real_portfolio_is_fully_admitted_with_explicit_scope() -> None:
    document = _admission()
    assert document["source_count"] == 7
    assert document["parser_input_count"] == 6
    assert document["typed_refusal_count"] == 1
    assert document["total_bytes"] == 5_589_384
    assert document["portfolio_scope"] == {
        "kind": "parser-qualification",
        "flagship_research_corpus": False,
        "scientific_claims_admitted": False,
    }
    assert set(document["checks"].values()) == {"passed"}
    assert all(source["state"] == "admitted" for source in document["sources"])


def test_ocr_specimen_is_admitted_only_as_typed_refusal() -> None:
    document = _admission()
    source = next(
        item for item in document["sources"] if item["format_id"] == "ocr-required"
    )
    assert source["qualification_outcome"] == "ocr-required"
    assert source["disposition"] == "verified_ocr_refusal"
    assert source["truth_roles"] == ["ocr-required-outcome"]


def test_admission_write_is_byte_stable_across_restart(tmp_path: Path) -> None:
    document = _admission()
    path = tmp_path / "parser-portfolio-admission.json"
    write_admission(path, document)
    first = path.read_bytes()
    write_admission(path, document)
    assert path.read_bytes() == first


def test_admission_rejects_noncanonical_source_identity() -> None:
    with pytest.raises(RuntimeError, match="not a full SHA"):
        build_admission(
            source_commit="short",
            portfolio_path=PORTFOLIO_ROOT / "sources.jsonl",
            output_root=PORTFOLIO_ROOT,
            lock_path=PORTFOLIO_ROOT / "corpus.lock.json",
            truth_path=PORTFOLIO_ROOT / "locator-truth.jsonl",
        )


def test_admission_identity_rejects_scope_tampering() -> None:
    document = deepcopy(_admission())
    document["portfolio_scope"]["flagship_research_corpus"] = True
    document["admission_identity_sha256"] = admission_identity(document)
    with pytest.raises(RuntimeError, match="scope drift"):
        validate_admission_document(document)


def test_admission_count_drift_is_rejected_even_with_new_identity() -> None:
    document = deepcopy(_admission())
    document["parser_input_count"] = 7
    document["admission_identity_sha256"] = admission_identity(document)
    with pytest.raises(RuntimeError, match="input count mismatch"):
        validate_admission_document(document)
