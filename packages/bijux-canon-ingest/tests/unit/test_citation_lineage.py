# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Exact citation lineage round trips over every admitted real format."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    AdmissionResult,
    CitationLineageError,
    CitationLineageErrorCode,
    DiscoveredSource,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    SemanticChunk,
    SemanticChunkingPolicy,
    SourceLocator,
    admit_source,
    build_document_citation_lineage,
    build_document_span_mappings,
    chunk_document_mappings,
    parse_docx,
    parse_html,
    parse_jats,
    parse_markdown,
    parse_pdf,
    parse_text,
    resolve_chunk_citation,
    resolve_source_locator,
)
from bijux_canon_ingest.domain.citation_lineage import (
    ParsedSourceDocument,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat

REPOSITORY = Path(__file__).parents[4]
EXAMPLES = REPOSITORY / "examples" / "document-formats"
POLICY = SemanticChunkingPolicy(max_characters=480, overlap_characters=48)
Parsed = (
    ParsedDocument
    | ParsedDocxDocument
    | ParsedHtmlDocument
    | ParsedPdfDocument
    | ParsedTextDocument
)
PARSERS: dict[SourceFormat, Callable[[AdmissionResult], Parsed]] = {
    "jats": parse_jats,
    "pdf-digital": parse_pdf,
    "html": parse_html,
    "markdown": parse_markdown,
    "text": parse_text,
    "docx": parse_docx,
}
EXPECTED_SCHEMES = {
    "jats": "jats-element-path",
    "pdf-digital": "pdf-page-text-span",
    "html": "html-dom-path",
    "markdown": "markdown-line-span",
    "text": "text-line-span",
    "docx": "ooxml-package-part-and-block-index",
}


def _artifact_id(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _parse(
    format_id: SourceFormat,
) -> tuple[bytes, ParsedSourceDocument, tuple[SemanticChunk, ...]]:
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
    document = PARSERS[format_id](admission)
    chunks = chunk_document_mappings(
        document,
        build_document_span_mappings(content, document),
        policy=POLICY,
    )
    return content, document, chunks


@pytest.mark.parametrize("format_id", tuple(PARSERS))
def test_real_format_chunk_resolves_through_hashed_locator_edges(
    format_id: SourceFormat,
) -> None:
    content, document, chunks = _parse(format_id)
    document_id = _artifact_id(format_id)
    lineage = build_document_citation_lineage(
        document=document,
        document_id=document_id,
        chunks=chunks,
    )
    chunk = chunks[0]

    resolved = resolve_chunk_citation(
        lineage=lineage,
        document=document,
        chunks=chunks,
        source_content=content,
        expected_document_id=document_id,
        chunk_id=chunk.chunk_id,
        character_start=0,
        character_end=len(chunk.normalized_text),
        expected_text_sha256=chunk.normalized_text_sha256,
    )

    assert resolved.exact_text == chunk.normalized_text
    assert resolved.exact_text_sha256 == chunk.normalized_text_sha256
    assert resolved.segments
    assert {segment.locator.scheme for segment in resolved.segments} == {
        EXPECTED_SCHEMES[format_id]
    }
    assert all(
        segment.source_span.resolve(content) == content for segment in resolved.segments
    )
    for segment in resolved.segments:
        assert segment.source_document_edge_sha256.startswith("sha256:")
        assert segment.document_mapping_edge_sha256.startswith("sha256:")
        assert segment.mapping_chunk_edge_sha256.startswith("sha256:")
        assert segment.segment_sha256.startswith("sha256:")
    assert lineage.lineage_sha256.startswith("sha256:")
    assert lineage.manifest() == lineage.manifest()


def test_unicode_offsets_resolve_by_code_point_with_exact_hash() -> None:
    content, document, chunks = _parse("jats")
    document_id = _artifact_id("unicode-jats")
    lineage = build_document_citation_lineage(
        document=document,
        document_id=document_id,
        chunks=chunks,
    )
    record = next(
        record
        for record in lineage.records
        if any(ord(character) > 127 for character in record.normalized_text)
    )
    start = next(
        index
        for index, character in enumerate(record.normalized_text)
        if ord(character) > 127
    )
    expected = record.normalized_text[start : start + 1]

    resolved = resolve_chunk_citation(
        lineage=lineage,
        document=document,
        chunks=chunks,
        source_content=content,
        expected_document_id=document_id,
        chunk_id=record.chunk_id,
        character_start=start,
        character_end=start + 1,
        expected_text_sha256=hashlib.sha256(expected.encode()).hexdigest(),
    )

    assert resolved.exact_text == expected
    assert len(resolved.exact_text) == 1


def test_duplicate_text_resolves_by_structural_locator_not_text_search() -> None:
    _, document, _ = _parse("jats")
    assert isinstance(document, ParsedDocument)
    duplicates: dict[str, list[SourceLocator]] = defaultdict(list)
    for block in document.blocks:
        duplicates[block.source_text].append(block.locator)
    locators = next(
        items for text, items in duplicates.items() if text and len(items) > 1
    )

    first = resolve_source_locator(document, locators[0])
    second = resolve_source_locator(document, locators[1])

    assert first == second
    assert locators[0] != locators[1]


def test_unavailable_and_ambiguous_locators_are_typed_refusals() -> None:
    _, document, _ = _parse("jats")
    assert isinstance(document, ParsedDocument)
    missing = SourceLocator("jats-element-path", (("element_path", "/missing[1]"),))

    with pytest.raises(CitationLineageError) as unavailable:
        resolve_source_locator(document, missing)
    assert unavailable.value.code is CitationLineageErrorCode.locator_unavailable

    duplicated = replace(
        document,
        blocks=(
            document.blocks[0],
            replace(document.blocks[1], locator=document.blocks[0].locator),
            *document.blocks[2:],
        ),
    )
    with pytest.raises(CitationLineageError) as ambiguous:
        resolve_source_locator(duplicated, document.blocks[0].locator)
    assert ambiguous.value.code is CitationLineageErrorCode.locator_ambiguous


def test_source_text_and_mapping_tampering_fail_closed() -> None:
    content, document, chunks = _parse("markdown")
    document_id = _artifact_id("tamper-markdown")
    lineage = build_document_citation_lineage(
        document=document,
        document_id=document_id,
        chunks=chunks,
    )
    chunk = chunks[0]
    arguments = {
        "lineage": lineage,
        "document": document,
        "chunks": chunks,
        "source_content": content,
        "expected_document_id": document_id,
        "chunk_id": chunk.chunk_id,
        "character_start": 0,
        "character_end": len(chunk.normalized_text),
        "expected_text_sha256": chunk.normalized_text_sha256,
    }

    with pytest.raises(CitationLineageError) as source_error:
        resolve_chunk_citation(**{**arguments, "source_content": content + b"tamper"})
    assert source_error.value.code is CitationLineageErrorCode.source_identity_mismatch

    with pytest.raises(CitationLineageError) as text_error:
        resolve_chunk_citation(**{**arguments, "expected_text_sha256": "0" * 64})
    assert text_error.value.code is CitationLineageErrorCode.text_identity_mismatch

    record = lineage.records[0]
    changed_segment = replace(
        record.segments[0],
        mapping_sha256=_artifact_id("tampered-mapping"),
    )
    changed_record = replace(
        record,
        segments=(changed_segment, *record.segments[1:]),
    )
    changed_lineage = replace(
        lineage,
        records=(changed_record, *lineage.records[1:]),
    )
    with pytest.raises(CitationLineageError) as mapping_error:
        resolve_chunk_citation(
            **{
                **arguments,
                "lineage": changed_lineage,
            }
        )
    assert (
        mapping_error.value.code is CitationLineageErrorCode.mapping_identity_mismatch
    )


def test_locator_selectors_have_one_canonical_order() -> None:
    first = SourceLocator("test", (("z", 1), ("a", "value")))
    second = SourceLocator("test", (("a", "value"), ("z", 1)))

    assert first == second
    assert first.selectors == (("a", "value"), ("z", 1))
