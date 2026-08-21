# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    DiscoveredSource,
    DocumentParseError,
    ParsedDocxDocument,
    admit_source,
    parse_docx,
)
from bijux_canon_ingest.infra.admission.docx import DOCX_MEDIA_TYPE

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_QUALIFICATION_SOURCE = (
    _REPOSITORY_ROOT / "examples/document-formats/corpus/parser-docx-real.docx"
)
_LOCATOR_TRUTH = _REPOSITORY_ROOT / "examples/document-formats/locator-truth.jsonl"


def _source(path: Path, *, media_type: str = DOCX_MEDIA_TYPE) -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name="docx-qualification",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.fixture(scope="module")
def qualification_document() -> ParsedDocxDocument:
    admission = admit_source(_source(_QUALIFICATION_SOURCE))
    assert admission.admitted is True
    return parse_docx(admission)


def test_docx_parser_preserves_real_properties_and_structure(
    qualification_document: ParsedDocxDocument,
) -> None:
    assert qualification_document.metadata.creator == "Brittany Benson-Cooper"
    assert qualification_document.metadata.last_modified_by == "Mallows, Rob - NISTA"
    assert qualification_document.metadata.created_at == "2020-09-24T14:17:00Z"
    assert qualification_document.metadata.modified_at == "2025-08-20T08:30:00Z"
    assert len(qualification_document.blocks) == 298
    assert {block.role for block in qualification_document.blocks} == {
        "title",
        "heading",
        "paragraph",
        "list-item",
        "table-cell",
        "hyperlink",
    }


def test_docx_parser_matches_independently_reviewed_package_truth(
    qualification_document: ParsedDocxDocument,
) -> None:
    rows = (
        json.loads(line)
        for line in _LOCATOR_TRUTH.read_text(encoding="utf-8").splitlines()
    )
    truth_rows = [row for row in rows if row["format_id"] == "docx"]

    assert len(truth_rows) == 6
    for truth in truth_rows:
        matches = [
            block
            for block in qualification_document.blocks
            if all(
                block.locator.get(name) == value
                for name, value in truth["locator"].items()
            )
        ]
        assert len(matches) == 1
        assert matches[0].role == truth["block_role"]
        assert matches[0].text == truth["exact_text"]
        assert matches[0].text_sha256 == truth["exact_text_sha256"]


def test_docx_parser_preserves_hyperlink_targets_and_footnotes(tmp_path: Path) -> None:
    path = tmp_path / "semantic.docx"
    content_types = b"""<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>"""
    document = b"""<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body><w:p><w:r><w:t>Report</w:t></w:r></w:p><w:p><w:hyperlink r:id="rId1"><w:r><w:t>Evidence</w:t></w:r></w:hyperlink></w:p></w:body></w:document>"""
    relationships = b"""<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.test/evidence" TargetMode="External"/></Relationships>"""
    footnotes = b"""<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:footnote w:id="1"><w:p><w:r><w:t>Exact note</w:t></w:r></w:p></w:footnote></w:footnotes>"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/footnotes.xml", footnotes)

    parsed = parse_docx(admit_source(_source(path)))
    hyperlink = next(block for block in parsed.blocks if block.role == "hyperlink")
    footnote = next(block for block in parsed.blocks if block.role == "footnote")

    assert hyperlink.text == "Evidence"
    assert hyperlink.target == "https://example.test/evidence"
    assert hyperlink.locator.get("hyperlink_index") == 1
    assert footnote.text == "Exact note"
    assert footnote.locator.get("package_part") == "word/footnotes.xml"


def test_docx_parser_is_deterministic_and_rechecks_source(
    qualification_document: ParsedDocxDocument,
    tmp_path: Path,
) -> None:
    repeated = parse_docx(admit_source(_source(_QUALIFICATION_SOURCE)))
    path = tmp_path / "changed.docx"
    original = _QUALIFICATION_SOURCE.read_bytes()
    path.write_bytes(original)
    admission = admit_source(_source(path))
    path.write_bytes(original + b"\n")

    assert qualification_document.manifest() == repeated.manifest()
    with pytest.raises(DocumentParseError) as raised:
        parse_docx(admission)
    assert raised.value.code == "source_changed"


def test_docx_parser_refuses_other_admitted_formats() -> None:
    with pytest.raises(DocumentParseError) as raised:
        parse_docx(
            admit_source(_source(_QUALIFICATION_SOURCE, media_type="application/zip"))
        )

    assert raised.value.code == "source_not_admitted"
