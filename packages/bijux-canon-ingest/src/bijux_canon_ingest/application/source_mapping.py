# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Build exact byte and locator mappings for parsed blocks and chunks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import TypeAlias

from bijux_canon_ingest.domain.document_extraction import (
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    SourceLocator,
)
from bijux_canon_ingest.domain.source_mapping import (
    NormalizedSpanMapping,
    SourceByteSpan,
    TextTransformation,
)

ParsedSourceDocument: TypeAlias = (
    ParsedDocument
    | ParsedPdfDocument
    | ParsedHtmlDocument
    | ParsedTextDocument
    | ParsedDocxDocument
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _text_sha256(value: str) -> str:
    return _sha256(value.encode("utf-8"))


def _configuration_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return _sha256(encoded)


def _format_id(document: ParsedSourceDocument) -> str:
    if isinstance(document, ParsedPdfDocument):
        return "pdf-digital"
    if isinstance(document, ParsedHtmlDocument):
        return "html"
    if isinstance(document, ParsedDocxDocument):
        return "docx"
    return document.format_id


def _text_items(
    document: ParsedSourceDocument,
) -> Iterable[tuple[str, str, SourceLocator]]:
    if isinstance(document, ParsedPdfDocument):
        return (
            (page.text, page.text, page.locator) for page in document.pages if page.text
        )
    if isinstance(document, ParsedDocument | ParsedHtmlDocument):
        return (
            (block.source_text, block.text, block.locator) for block in document.blocks
        )
    return ((block.text, block.text, block.locator) for block in document.blocks)


def build_document_span_mappings(
    source_content: bytes,
    document: ParsedSourceDocument,
) -> tuple[NormalizedSpanMapping, ...]:
    """Map every non-empty parsed block to source bytes and its human locator."""

    source_sha256 = _sha256(source_content)
    if source_sha256 != document.source_content_sha256:
        raise ValueError(
            "parsed document and supplied source bytes have different identities"
        )
    source_span = SourceByteSpan(
        start=0,
        end=len(source_content),
        selected_bytes_sha256=source_sha256,
    )
    format_id = _format_id(document)
    mappings: list[NormalizedSpanMapping] = []
    for original_text, normalized_text, locator in _text_items(document):
        original_sha256 = _text_sha256(original_text)
        normalized_sha256 = _text_sha256(normalized_text)
        selection = TextTransformation(
            operation="segment",
            implementation=f"bijux-canon-ingest-{document.parser_name}-{format_id}",
            implementation_version=document.parser_version,
            configuration_sha256=_configuration_sha256(
                {
                    "format_id": format_id,
                    "locator": locator.manifest(),
                    "operation": "parser-selection",
                }
            ),
            input_content_sha256=source_sha256,
            output_content_sha256=original_sha256,
        )
        transformations = [selection]
        if original_text != normalized_text:
            transformations.append(
                TextTransformation(
                    operation="whitespace_normalize",
                    implementation="bijux-canon-ingest-semantic-whitespace",
                    implementation_version="1",
                    configuration_sha256=_configuration_sha256(
                        {"collapse_whitespace": True, "trim": True}
                    ),
                    input_content_sha256=original_sha256,
                    output_content_sha256=normalized_sha256,
                )
            )
        mappings.append(
            NormalizedSpanMapping(
                source_content_sha256=source_sha256,
                source_span=source_span,
                locator=locator,
                normalized_text=normalized_text,
                original_text_sha256=original_sha256,
                normalized_start=0,
                normalized_end=len(normalized_text),
                transformations=tuple(transformations),
            )
        )
    return tuple(mappings)


def build_chunk_span_mapping(
    parent: NormalizedSpanMapping,
    *,
    start: int,
    end: int,
) -> NormalizedSpanMapping:
    """Map one exact normalized chunk span through its parent block lineage."""

    if start < 0 or end <= start or end > len(parent.normalized_text):
        raise ValueError("chunk span must be non-empty and within its parent mapping")
    text = parent.normalized_text[start:end]
    transformation = TextTransformation(
        operation="segment",
        implementation="bijux-canon-ingest-normalized-span-segmenter",
        implementation_version="1",
        configuration_sha256=_configuration_sha256(
            {"coordinate_system": "unicode_code_point", "end": end, "start": start}
        ),
        input_content_sha256=parent.normalized_text_sha256,
        output_content_sha256=_text_sha256(text),
    )
    return NormalizedSpanMapping(
        source_content_sha256=parent.source_content_sha256,
        source_span=parent.source_span,
        locator=parent.locator,
        normalized_text=text,
        original_text_sha256=parent.original_text_sha256,
        normalized_start=parent.normalized_start + start,
        normalized_end=parent.normalized_start + end,
        transformations=(*parent.transformations, transformation),
        parent_mapping_sha256=parent.mapping_sha256,
    )


__all__ = [
    "ParsedSourceDocument",
    "build_chunk_span_mapping",
    "build_document_span_mappings",
]
