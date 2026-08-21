# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    DiscoveredSource,
    DocumentParseError,
    ParsedDocument,
    admit_source,
    parse_jats,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_QUALIFICATION_SOURCE = (
    _REPOSITORY_ROOT / "examples/document-formats/corpus/parser-jats-real.xml"
)
_LOCATOR_TRUTH = _REPOSITORY_ROOT / "examples/document-formats/locator-truth.jsonl"
_ANCIENT_DNA_SOURCES = (
    _REPOSITORY_ROOT / "examples/ancient-dna-research/corpus/sources"
)
_REQUIRED_ROLES = {
    "title",
    "abstract",
    "section-heading",
    "paragraph",
    "caption",
    "table",
    "reference",
}
_TRUTH_ROLE = {
    "article-title": "title",
    "abstract-paragraph": "abstract",
    "body-section-heading": "section-heading",
    "body-paragraph": "paragraph",
    "reference": "reference",
}


def _source(
    path: Path,
    *,
    root_name: str = "research",
    media_type: str = "application/xml",
) -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name=root_name,
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.fixture(scope="module")
def qualification_document() -> ParsedDocument:
    admission = admit_source(_source(_QUALIFICATION_SOURCE, root_name="qualification"))
    assert admission.admitted is True
    return parse_jats(admission)


def test_jats_parser_extracts_required_metadata_and_structure(
    qualification_document: ParsedDocument,
) -> None:
    metadata = qualification_document.metadata

    assert metadata.title == (
        "Ancient RNA from Late Pleistocene permafrost and historical canids shows "
        "tissue-specific transcriptome survival"
    )
    assert metadata.doi == "10.1371/journal.pbio.3000166"
    assert metadata.journal == "PLOS Biology"
    assert metadata.publication_year == 2019
    assert len(metadata.authors) == 7
    assert metadata.authors[0] == "Oliver Smith"
    assert metadata.authors[-1] == "M. T. P. Gilbert"
    assert metadata.license_url == "http://creativecommons.org/licenses/by/4.0/"
    assert "Creative Commons Attribution License" in metadata.license_text
    assert metadata.language == "en"
    assert {block.role for block in qualification_document.blocks} == _REQUIRED_ROLES
    introduction = next(
        block
        for block in qualification_document.blocks
        if block.role == "section-heading" and block.text == "Introduction"
    )
    assert introduction.section_path == ("Introduction",)


def test_jats_parser_matches_independently_reviewed_locator_truth(
    qualification_document: ParsedDocument,
) -> None:
    rows = (
        json.loads(line)
        for line in _LOCATOR_TRUTH.read_text(encoding="utf-8").splitlines()
    )
    truth_rows = [row for row in rows if row["format_id"] == "jats"]
    blocks_by_path = {
        block.locator.get("element_path"): block
        for block in qualification_document.blocks
    }

    assert len(truth_rows) == 5
    for truth in truth_rows:
        block = blocks_by_path[truth["locator"]["element_path"]]
        assert block.role == _TRUTH_ROLE[truth["block_role"]]
        assert block.text == truth["exact_text"]
        assert block.text_sha256 == truth["exact_text_sha256"]


def test_jats_parser_manifest_is_deterministic(
    qualification_document: ParsedDocument,
) -> None:
    repeated = parse_jats(
        admit_source(_source(_QUALIFICATION_SOURCE, root_name="qualification"))
    )

    assert qualification_document.manifest() == repeated.manifest()
    assert qualification_document.manifest()["manifest_sha256"].startswith("sha256:")


def test_jats_parser_handles_every_locked_ancient_dna_article() -> None:
    paths = sorted(_ANCIENT_DNA_SOURCES.glob("*.xml"))

    assert len(paths) == 8
    for path in paths:
        admission = admit_source(_source(path))
        assert admission.admitted is True, path.name
        document = parse_jats(admission)
        assert {block.role for block in document.blocks} == _REQUIRED_ROLES, path.name
        assert document.metadata.doi.startswith("10.1371/"), path.name


def test_jats_parser_rechecks_source_identity_after_admission(tmp_path: Path) -> None:
    path = tmp_path / "article.xml"
    original = _QUALIFICATION_SOURCE.read_bytes()
    path.write_bytes(original)
    admission = admit_source(_source(path))
    path.write_bytes(original.replace(b"Ancient RNA", b"Altered RNA", 1))

    with pytest.raises(DocumentParseError) as raised:
        parse_jats(admission)

    assert raised.value.code == "source_changed"


def test_jats_parser_refuses_rejected_and_other_format_admissions(
    tmp_path: Path,
) -> None:
    malformed_path = tmp_path / "malformed.xml"
    malformed_path.write_bytes(b"<article>")
    text_path = tmp_path / "notes.txt"
    text_path.write_text("evidence", encoding="utf-8")
    text_source = _source(text_path, media_type="text/plain")

    with pytest.raises(DocumentParseError) as rejected:
        parse_jats(admit_source(_source(malformed_path)))
    with pytest.raises(DocumentParseError) as mismatch:
        parse_jats(admit_source(text_source))

    assert rejected.value.code == "source_not_admitted"
    assert mismatch.value.code == "format_mismatch"
