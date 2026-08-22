# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    AdmissionResult,
    DiscoveredSource,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    admit_source,
    build_chunk_span_mapping,
    build_document_span_mappings,
    parse_docx,
    parse_html,
    parse_jats,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat

Parsed = (
    ParsedDocument
    | ParsedDocxDocument
    | ParsedHtmlDocument
    | ParsedPdfDocument
    | ParsedTextDocument
)

REPOSITORY = Path(__file__).parents[4]
EXAMPLES = REPOSITORY / "examples" / "document-formats"
PARSERS: dict[SourceFormat, Callable[[AdmissionResult], Parsed]] = {
    "jats": parse_jats,
    "pdf-digital": parse_pdf,
    "html": parse_html,
    "markdown": parse_markdown,
    "text": parse_text,
    "docx": parse_docx,
}


def _parse(format_id: SourceFormat) -> tuple[bytes, Parsed]:
    receipt = json.loads(
        (
            EXAMPLES / "acquisition-receipts" / f"parser-{format_id}-real.json"
        ).read_text()
    )
    path = EXAMPLES / receipt["local_path"]
    content = path.read_bytes()
    source = DiscoveredSource.create(
        root_name="parser-corpus",
        relative_path=receipt["local_path"],
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=(
            "text/markdown" if format_id == "markdown" else receipt["media_type"]
        ),
        is_symlink=False,
    )
    admission = admit_source(source)
    assert admission.admitted
    return content, PARSERS[format_id](admission)


@pytest.mark.parametrize("format_id", tuple(PARSERS))
def test_maps_every_real_parsed_block_to_source_bytes(
    format_id: SourceFormat,
) -> None:
    content, document = _parse(format_id)
    mappings = build_document_span_mappings(content, document)
    expected_count = (
        sum(bool(page.text) for page in document.pages)
        if isinstance(document, ParsedPdfDocument)
        else len(document.blocks)
    )

    assert len(mappings) == expected_count
    assert all(mapping.resolve_source_bytes(content) == content for mapping in mappings)
    assert all(mapping.source_span.start == 0 for mapping in mappings)
    assert all(mapping.source_span.end == len(content) for mapping in mappings)
    assert all(
        mapping.transformations[-1].output_content_sha256
        == mapping.normalized_text_sha256
        for mapping in mappings
    )
    assert len({mapping.mapping_sha256 for mapping in mappings}) == len(mappings)
    assert mappings[0].manifest() == mappings[0].manifest()


def test_chunk_mapping_preserves_parent_and_exact_character_span() -> None:
    content, document = _parse("jats")
    parent = build_document_span_mappings(content, document)[0]
    chunk = build_chunk_span_mapping(parent, start=1, end=12)

    assert chunk.normalized_text == parent.normalized_text[1:12]
    assert chunk.normalized_start == 1
    assert chunk.normalized_end == 12
    assert chunk.parent_mapping_sha256 == parent.mapping_sha256
    assert chunk.locator == parent.locator
    assert chunk.resolve_source_bytes(content) == content
    assert chunk.transformations[:-1] == parent.transformations
    assert chunk.transformations[-1].input_content_sha256 == (
        parent.normalized_text_sha256
    )


def test_mapping_rejects_stale_source_bytes() -> None:
    content, document = _parse("text")
    mapping = build_document_span_mappings(content, document)[0]

    with pytest.raises(ValueError, match="source identity"):
        mapping.resolve_source_bytes(content + b"altered")
    with pytest.raises(ValueError, match="different identities"):
        build_document_span_mappings(content + b"altered", document)


def test_mapping_rejects_broken_transformation_hash_chain() -> None:
    content, document = _parse("html")
    mapping = next(
        item
        for item in build_document_span_mappings(content, document)
        if len(item.transformations) > 1
    )
    broken = replace(
        mapping.transformations[0],
        output_content_sha256="0" * 64,
    )

    with pytest.raises(ValueError, match="transformation hashes"):
        replace(mapping, transformations=(broken, *mapping.transformations[1:]))


@pytest.mark.parametrize(("start", "end"), [(-1, 2), (2, 2), (0, 10_000)])
def test_chunk_mapping_rejects_invalid_parent_spans(start: int, end: int) -> None:
    content, document = _parse("markdown")
    parent = build_document_span_mappings(content, document)[0]

    with pytest.raises(ValueError, match="within its parent"):
        build_chunk_span_mapping(parent, start=start, end=end)
