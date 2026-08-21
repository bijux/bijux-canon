"""Identity, drift, and restart checks for the parser-source lock."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil

import pytest

from bijux_canon_dev.corpus.parser_lock import (
    build_lock,
    validate_lock_document,
    write_lock,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_ROOT = REPO_ROOT / "examples/document-formats"


def _real_lock() -> dict[str, object]:
    return build_lock(
        portfolio_path=PORTFOLIO_ROOT / "sources.jsonl",
        output_root=PORTFOLIO_ROOT,
    )


def test_real_portfolio_builds_complete_identity_lock() -> None:
    document = _real_lock()
    assert document["schema_version"] == "bijux.canon.parser_source_lock.v1"
    assert document["source_count"] == 7
    assert document["total_bytes"] == 5_589_384
    sources = document["sources"]
    assert isinstance(sources, list)
    assert {source["format_id"] for source in sources} == {
        "jats",
        "pdf-digital",
        "html",
        "markdown",
        "text",
        "docx",
        "ocr-required",
    }
    assert all(source["license_evidence_sha256"] for source in sources)
    assert all(source["retrieved_at"].endswith("Z") for source in sources)


def test_lock_write_is_byte_stable_across_restart(tmp_path: Path) -> None:
    document = _real_lock()
    path = tmp_path / "corpus.lock.json"
    write_lock(path, document)
    first = path.read_bytes()
    write_lock(path, document)
    assert path.read_bytes() == first
    assert json.loads(first)["lock_identity_sha256"] == document["lock_identity_sha256"]


def test_lock_identity_rejects_metadata_tampering() -> None:
    document = _real_lock()
    tampered = deepcopy(document)
    tampered["sources"][0]["attribution"] = "changed"
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_lock_document(tampered)


def test_builder_rejects_media_byte_drift(tmp_path: Path) -> None:
    copied = tmp_path / "document-formats"
    shutil.copytree(PORTFOLIO_ROOT, copied)
    media = copied / "corpus/parser-markdown-real.md"
    os.chmod(media, 0o644)
    media.write_bytes(media.read_bytes() + b"\nchanged\n")
    with pytest.raises(RuntimeError, match="receipt drift"):
        build_lock(portfolio_path=copied / "sources.jsonl", output_root=copied)


def test_transformed_html_contains_no_excluded_interface_material() -> None:
    document = _real_lock()
    sources = document["sources"]
    html = next(source for source in sources if source["format_id"] == "html")
    assert html["transformations"] == ["extract-licensed-plos-article-html-v1"]
    body = (PORTFOLIO_ROOT / html["local_path"]).read_bytes().lower()
    assert all(
        marker not in body
        for marker in (b"<script", b"<style", b"<iframe", b"<img", b"article-tabs")
    )
