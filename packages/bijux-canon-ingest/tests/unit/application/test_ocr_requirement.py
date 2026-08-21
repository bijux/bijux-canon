# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pypdf import PdfWriter

from bijux_canon_ingest import (
    DiscoveredSource,
    DocumentParseError,
    admit_source,
    assess_ocr_requirement,
)

_ROOT = Path(__file__).resolve().parents[5]
_IMAGE = _ROOT / "examples/document-formats/corpus/parser-ocr-required-real.jpg"


def _source(path: Path, media_type: str) -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name="ocr-qualification",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


def test_real_image_returns_exact_typed_ocr_requirement() -> None:
    outcome = assess_ocr_requirement(admit_source(_source(_IMAGE, "image/jpeg")))

    assert outcome.locator.scheme == "image-region"
    assert dict(outcome.locator.selectors) == {
        "x": 0,
        "y": 0,
        "width": 4886,
        "height": 3648,
        "unit": "pixel",
    }
    assert outcome.manifest()["ocr_performed"] is False
    assert outcome.manifest()["text"] is None
    assert outcome.manifest()["ocr_provider_status"] == "not-admitted"


def test_image_only_pdf_returns_page_bounded_requirement(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)

    outcome = assess_ocr_requirement(admit_source(_source(path, "application/pdf")))

    assert outcome.page_count == 1
    assert dict(outcome.locator.selectors) == {"page_start": 1, "page_end": 1}


def test_ocr_assessment_rechecks_source_and_refuses_text(tmp_path: Path) -> None:
    changed = tmp_path / "changed.jpg"
    original = _IMAGE.read_bytes()
    changed.write_bytes(original)
    admission = admit_source(_source(changed, "image/jpeg"))
    changed.write_bytes(original + b"\x00")
    text = tmp_path / "notes.txt"
    text.write_text("digital evidence", encoding="utf-8")

    with pytest.raises(DocumentParseError) as source_error:
        assess_ocr_requirement(admission)
    with pytest.raises(DocumentParseError) as format_error:
        assess_ocr_requirement(admit_source(_source(text, "text/plain")))

    assert source_error.value.code == "source_changed"
    assert format_error.value.code == "format_mismatch"
