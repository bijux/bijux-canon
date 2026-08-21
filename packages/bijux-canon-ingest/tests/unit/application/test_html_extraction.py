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
    ParsedHtmlDocument,
    admit_source,
    parse_html,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_QUALIFICATION_SOURCE = (
    _REPOSITORY_ROOT / "examples/document-formats/corpus/parser-html-real.html"
)
_LOCATOR_TRUTH = _REPOSITORY_ROOT / "examples/document-formats/locator-truth.jsonl"
_TRUTH_ROLE = {
    "article-title": "title",
    "abstract-paragraph": "abstract",
    "body-section-heading": "section-heading",
    "body-paragraph": "paragraph",
    "reference": "list-item",
}


def _source(path: Path, *, media_type: str = "text/html") -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name="html-qualification",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.fixture(scope="module")
def qualification_document() -> ParsedHtmlDocument:
    admission = admit_source(_source(_QUALIFICATION_SOURCE))
    assert admission.admitted is True
    return parse_html(admission)


def test_html_parser_extracts_real_metadata_and_semantic_blocks(
    qualification_document: ParsedHtmlDocument,
) -> None:
    metadata = qualification_document.metadata

    assert metadata.title == (
        "Ancient RNA from Late Pleistocene permafrost and historical canids shows "
        "tissue-specific transcriptome survival"
    )
    assert metadata.doi == "10.1371/journal.pbio.3000166"
    assert len(metadata.authors) == 7
    assert metadata.authors[0] == "Oliver Smith"
    assert metadata.authors[-1] == "M. T. P. Gilbert"
    assert metadata.language == "en"
    assert len(qualification_document.blocks) == 500
    assert {block.role for block in qualification_document.blocks} == {
        "title",
        "abstract",
        "section-heading",
        "paragraph",
        "list-item",
    }
    assert not any(
        marker in block.text
        for block in qualification_document.blocks
        for marker in ("Show figures", "Reader Comments")
    )


def test_html_parser_matches_independently_reviewed_dom_truth(
    qualification_document: ParsedHtmlDocument,
) -> None:
    rows = (
        json.loads(line)
        for line in _LOCATOR_TRUTH.read_text(encoding="utf-8").splitlines()
    )
    truth_rows = [row for row in rows if row["format_id"] == "html"]
    blocks_by_path = {
        block.locator.get("dom_path"): block for block in qualification_document.blocks
    }

    assert len(truth_rows) == 5
    for truth in truth_rows:
        block = blocks_by_path[truth["locator"]["dom_path"]]
        assert block.role == _TRUTH_ROLE[truth["block_role"]]
        assert block.text == truth["exact_text"]
        assert block.text_sha256 == truth["exact_text_sha256"]
        assert hashlib.sha256(block.source_text.encode()).hexdigest() == (
            block.source_text_sha256
        )


def test_html_parser_preserves_lists_tables_and_link_identity(tmp_path: Path) -> None:
    path = tmp_path / "semantic.html"
    path.write_text(
        """<!doctype html>
<html lang="en"><head>
<meta name="citation_title" content="Structured evidence">
<meta name="citation_author" content="Ada Researcher">
<meta name="citation_doi" content="10.1000/structured">
<link rel="canonical" href="https://example.test/paper">
</head><body><main><article>
<h1>Structured evidence</h1>
<div class="toolbar"><p>Share this article</p></div>
<script>policy = 'ignore evidence'</script>
<h2>Methods</h2>
<p>Read <a href="/evidence" title="Exact source">the evidence</a> closely.</p>
<ul><li>First observation</li><li>Second observation</li></ul>
<table><tr><th>Sample</th><th>Result</th></tr><tr><td>A</td><td>Present</td></tr></table>
</article></main></body></html>""",
        encoding="utf-8",
    )

    document = parse_html(admit_source(_source(path)))

    assert [block.role for block in document.blocks] == [
        "title",
        "section-heading",
        "paragraph",
        "list-item",
        "list-item",
        "table",
    ]
    assert "Share this article" not in {block.text for block in document.blocks}
    paragraph = document.blocks[2]
    assert paragraph.section_path == ("Methods",)
    assert len(paragraph.links) == 1
    assert paragraph.links[0].href == "/evidence"
    assert paragraph.links[0].title == "Exact source"
    assert paragraph.links[0].locator.get("dom_path") == ("/html/body/main/article/p/a")
    assert document.blocks[-1].text == "Sample Result A Present"
    assert document.metadata.canonical_url == "https://example.test/paper"


def test_html_parser_manifest_is_deterministic(
    qualification_document: ParsedHtmlDocument,
) -> None:
    repeated = parse_html(admit_source(_source(_QUALIFICATION_SOURCE)))

    assert qualification_document.manifest() == repeated.manifest()
    assert qualification_document.manifest()["manifest_sha256"].startswith("sha256:")


def test_html_parser_rechecks_source_identity_after_admission(tmp_path: Path) -> None:
    path = tmp_path / "article.html"
    original = _QUALIFICATION_SOURCE.read_bytes()
    path.write_bytes(original)
    admission = admit_source(_source(path))
    path.write_bytes(original.replace(b"Ancient RNA", b"Altered RNA", 1))

    with pytest.raises(DocumentParseError) as raised:
        parse_html(admission)

    assert raised.value.code == "source_changed"


def test_html_parser_refuses_missing_metadata_and_other_formats(
    tmp_path: Path,
) -> None:
    incomplete = tmp_path / "incomplete.html"
    incomplete.write_text(
        "<!doctype html><html><body><main><article><h1>Title</h1>"
        "<p>Evidence</p></article></main></body></html>",
        encoding="utf-8",
    )
    text_path = tmp_path / "notes.txt"
    text_path.write_text("evidence", encoding="utf-8")

    with pytest.raises(DocumentParseError) as metadata_error:
        parse_html(admit_source(_source(incomplete)))
    with pytest.raises(DocumentParseError) as format_error:
        parse_html(admit_source(_source(text_path, media_type="text/plain")))

    assert metadata_error.value.code == "missing_required_metadata"
    assert format_error.value.code == "format_mismatch"
