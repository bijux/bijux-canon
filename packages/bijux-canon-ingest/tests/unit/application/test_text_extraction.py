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
    ParsedTextDocument,
    SourceLocator,
    admit_source,
    parse_markdown,
    parse_text,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_CORPUS = _REPOSITORY_ROOT / "examples/document-formats/corpus"
_MARKDOWN_SOURCE = _CORPUS / "parser-markdown-real.md"
_TEXT_SOURCE = _CORPUS / "parser-text-real.txt"
_LOCATOR_TRUTH = _REPOSITORY_ROOT / "examples/document-formats/locator-truth.jsonl"
_TRUTH_ROLES = {
    "markdown": {
        "heading": "heading",
        "paragraph": "paragraph",
        "list-item": "list-item",
        "table-row": "table-row",
        "code-block": "code-block",
        "link": "link",
    },
    "text": {
        "title": "title",
        "section-heading": "section-heading",
        "paragraph": "paragraph",
        "list-item": "list-item",
        "syntax-example": "syntax-example",
        "reference": "reference",
    },
}


def _source(path: Path, *, media_type: str) -> DiscoveredSource:
    content = path.read_bytes()
    return DiscoveredSource.create(
        root_name="text-qualification",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.fixture(scope="module")
def markdown_document() -> ParsedTextDocument:
    admission = admit_source(_source(_MARKDOWN_SOURCE, media_type="text/markdown"))
    assert admission.admitted is True
    return parse_markdown(admission)


@pytest.fixture(scope="module")
def text_document() -> ParsedTextDocument:
    admission = admit_source(_source(_TEXT_SOURCE, media_type="text/plain"))
    assert admission.admitted is True
    return parse_text(admission)


def test_markdown_parser_preserves_real_semantic_boundaries(
    markdown_document: ParsedTextDocument,
) -> None:
    assert markdown_document.encoding == "utf-8"
    assert markdown_document.newline_style == "lf"
    assert len(markdown_document.blocks) == 78
    assert {block.role for block in markdown_document.blocks} == {
        "front-matter",
        "heading",
        "paragraph",
        "block-quote",
        "link",
        "table-row",
        "comment",
        "list-item",
        "code-block",
    }


def test_plain_text_parser_preserves_bom_and_rfc_structure(
    text_document: ParsedTextDocument,
) -> None:
    assert text_document.encoding == "utf-8-sig"
    assert text_document.newline_style == "lf"
    assert len(text_document.blocks) == 2553
    assert {block.role for block in text_document.blocks} == {
        "title",
        "section-heading",
        "paragraph",
        "list-item",
        "syntax-example",
        "reference",
    }


@pytest.mark.parametrize("format_id", ["markdown", "text"])
def test_text_parsers_match_independently_reviewed_line_truth(
    format_id: str,
    markdown_document: ParsedTextDocument,
    text_document: ParsedTextDocument,
) -> None:
    document = markdown_document if format_id == "markdown" else text_document
    rows = (
        json.loads(line)
        for line in _LOCATOR_TRUTH.read_text(encoding="utf-8").splitlines()
    )
    truth_rows = [row for row in rows if row["format_id"] == format_id]
    blocks_by_lines = {
        (block.locator.get("line_start"), block.locator.get("line_end")): block
        for block in document.blocks
    }

    assert len(truth_rows) == 6
    for truth in truth_rows:
        key = (truth["locator"]["line_start"], truth["locator"]["line_end"])
        block = blocks_by_lines[key]
        assert block.role == _TRUTH_ROLES[format_id][truth["block_role"]]
        assert block.text == truth["exact_text"]
        assert block.text_sha256 == truth["exact_text_sha256"]
        assert document.resolve_text(block.locator) == truth["exact_text"]


def test_text_parser_normalizes_crlf_with_exact_character_spans(tmp_path: Path) -> None:
    path = tmp_path / "windows.txt"
    path.write_bytes(b"\xef\xbb\xbfTitle\r\n\r\nFirst line\r\nSecond line\r\n")

    document = parse_text(admit_source(_source(path, media_type="text/plain")))

    assert document.encoding == "utf-8-sig"
    assert document.newline_style == "crlf"
    assert document.normalized_text == "Title\n\nFirst line\nSecond line\n"
    assert [block.text for block in document.blocks] == [
        "Title",
        "First line\nSecond line",
    ]
    assert all(
        document.resolve_text(block.locator) == block.text for block in document.blocks
    )


def test_text_parser_manifest_is_deterministic(
    markdown_document: ParsedTextDocument,
    text_document: ParsedTextDocument,
) -> None:
    repeated_markdown = parse_markdown(
        admit_source(_source(_MARKDOWN_SOURCE, media_type="text/markdown"))
    )
    repeated_text = parse_text(
        admit_source(_source(_TEXT_SOURCE, media_type="text/plain"))
    )

    assert markdown_document.manifest() == repeated_markdown.manifest()
    assert text_document.manifest() == repeated_text.manifest()


def test_markdown_parser_rechecks_source_and_fence_integrity(tmp_path: Path) -> None:
    changed_path = tmp_path / "changed.md"
    original = _MARKDOWN_SOURCE.read_bytes()
    changed_path.write_bytes(original)
    admission = admit_source(_source(changed_path, media_type="text/markdown"))
    changed_path.write_bytes(original + b"\n")
    broken_path = tmp_path / "broken.md"
    broken_path.write_text("# Heading\n\n```python\nprint('open')\n", encoding="utf-8")

    with pytest.raises(DocumentParseError) as changed:
        parse_markdown(admission)
    with pytest.raises(DocumentParseError) as broken:
        parse_markdown(admit_source(_source(broken_path, media_type="text/markdown")))

    assert changed.value.code == "source_changed"
    assert broken.value.code == "malformed_document"


def test_text_parsers_refuse_format_mismatch_and_stale_locator(
    markdown_document: ParsedTextDocument,
) -> None:
    text_admission = admit_source(_source(_TEXT_SOURCE, media_type="text/plain"))
    block = markdown_document.blocks[0]
    stale = SourceLocator(
        scheme="markdown-line-span",
        selectors=tuple(
            (name, "0" * 64 if name == "normalized_text_sha256" else value)
            for name, value in block.locator.selectors
        ),
    )
    wrong_line = SourceLocator(
        scheme="markdown-line-span",
        selectors=tuple(
            (
                name,
                value + 1 if name == "line_start" and isinstance(value, int) else value,
            )
            for name, value in block.locator.selectors
        ),
    )

    with pytest.raises(DocumentParseError) as mismatch:
        parse_markdown(text_admission)
    with pytest.raises(DocumentParseError) as locator_error:
        markdown_document.resolve_text(stale)
    with pytest.raises(DocumentParseError) as line_error:
        markdown_document.resolve_text(wrong_line)

    assert mismatch.value.code == "format_mismatch"
    assert locator_error.value.code == "invalid_locator"
    assert line_error.value.code == "invalid_locator"
