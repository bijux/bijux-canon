# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pypdf import PdfWriter
import pytest

from bijux_canon_ingest import (
    DiscoveredSource,
    DocumentParseError,
    ParsedPdfDocument,
    SourceLocator,
    admit_source,
    parse_pdf,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_QUALIFICATION_SOURCE = (
    _REPOSITORY_ROOT / "examples/document-formats/corpus/parser-pdf-digital-real.pdf"
)
_LOCATOR_TRUTH = _REPOSITORY_ROOT / "examples/document-formats/locator-truth.jsonl"


def _source(path: Path, *, media_type: str = "application/pdf") -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name="pdf-qualification",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.fixture(scope="module")
def qualification_document() -> ParsedPdfDocument:
    admission = admit_source(_source(_QUALIFICATION_SOURCE))
    assert admission.admitted is True
    return parse_pdf(admission)


def test_pdf_parser_preserves_ordered_pages_geometry_and_metadata(
    qualification_document: ParsedPdfDocument,
) -> None:
    assert len(qualification_document.pages) == 28
    assert [page.page_number for page in qualification_document.pages] == list(
        range(1, 29)
    )
    assert all(
        page.extraction_method == "digital-text"
        for page in qualification_document.pages
    )
    assert all(
        page.width_points > 0 and page.height_points > 0
        for page in qualification_document.pages
    )
    assert qualification_document.metadata.title == (
        "Ancient RNA from Late Pleistocene permafrost and historical canids shows "
        "tissue-specific transcriptome survival"
    )
    assert qualification_document.metadata.author is not None
    assert qualification_document.metadata.author.startswith("Oliver Smith")
    assert qualification_document.extractor == "pypdf-6.15.0-page-extract-text"


def test_pdf_parser_resolves_independently_reviewed_page_spans(
    qualification_document: ParsedPdfDocument,
) -> None:
    rows = (
        json.loads(line)
        for line in _LOCATOR_TRUTH.read_text(encoding="utf-8").splitlines()
    )
    truth_rows = [row for row in rows if row["format_id"] == "pdf-digital"]

    assert len(truth_rows) == 5
    for truth in truth_rows:
        locator = SourceLocator(
            scheme=truth["locator_scheme"],
            selectors=tuple(truth["locator"].items()),
        )
        resolved = qualification_document.resolve_text(locator)
        assert resolved == truth["exact_text"]
        assert (
            hashlib.sha256(resolved.encode("utf-8")).hexdigest()
            == truth["exact_text_sha256"]
        )


def test_pdf_parser_manifest_is_deterministic(
    qualification_document: ParsedPdfDocument,
) -> None:
    repeated = parse_pdf(admit_source(_source(_QUALIFICATION_SOURCE)))

    assert qualification_document.manifest() == repeated.manifest()
    assert qualification_document.manifest()["manifest_sha256"].startswith("sha256:")


def test_pdf_parser_refuses_image_only_documents_without_claiming_ocr(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with path.open("wb") as handle:
        writer.write(handle)
    admission = admit_source(_source(path))

    assert admission.admitted is True
    with pytest.raises(DocumentParseError) as raised:
        parse_pdf(admission)

    assert raised.value.code == "ocr_required"


def test_pdf_parser_reports_encryption_before_extraction(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    with path.open("wb") as handle:
        writer.write(handle)
    admission = admit_source(_source(path))

    assert admission.admitted is False
    with pytest.raises(DocumentParseError) as raised:
        parse_pdf(admission)

    assert raised.value.code == "encrypted_document"


def test_pdf_parser_rechecks_identity_and_locator_integrity(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    original = _QUALIFICATION_SOURCE.read_bytes()
    path.write_bytes(original)
    admission = admit_source(_source(path))
    path.write_bytes(original + b"\n")

    with pytest.raises(DocumentParseError) as changed:
        parse_pdf(admission)

    assert changed.value.code == "source_changed"
    document = parse_pdf(admit_source(_source(_QUALIFICATION_SOURCE)))
    invalid = SourceLocator(
        scheme="pdf-page-text-span",
        selectors=(
            ("extractor", document.extractor),
            ("page_number", 1),
            ("page_text_sha256", "0" * 64),
            ("text_start", 0),
            ("text_end", 1),
        ),
    )
    with pytest.raises(DocumentParseError) as locator_error:
        document.resolve_text(invalid)

    assert locator_error.value.code == "invalid_locator"
