# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Adapt parser-owned metadata into the canonical metadata resolver."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import date, datetime
from typing import cast

import yaml

from bijux_canon_ingest.application.source_mapping import ParsedSourceDocument
from bijux_canon_ingest.application.source_metadata import SourceMetadataRecord
from bijux_canon_ingest.domain.document_extraction import (
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat


def _format_id(document: ParsedSourceDocument) -> SourceFormat:
    if isinstance(document, ParsedPdfDocument):
        return "pdf-digital"
    if isinstance(document, ParsedHtmlDocument):
        return "html"
    if isinstance(document, ParsedDocxDocument):
        return "docx"
    return cast(SourceFormat, document.format_id)


def _first_block_title(document: ParsedSourceDocument) -> str | None:
    if isinstance(document, ParsedPdfDocument):
        return document.metadata.title
    blocks = document.blocks
    return next(
        (
            block.text
            for block in blocks
            if block.role == "title" and block.text.strip()
        ),
        None,
    )


def _first(values: Sequence[tuple[str, str]], *names: str) -> str | None:
    return next(
        (value for name, value in values if name.casefold() in names and value.strip()),
        None,
    )


def _authors(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value.strip():
        return (value,)
    if (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and all(isinstance(item, str) and item.strip() for item in value)
    ):
        return tuple(cast(Sequence[str], value))
    return ()


def _optional_text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return None


def _license_expression(text: str | None, url: str | None) -> str | None:
    normalized_url = (url or "").casefold().rstrip("/")
    expressions = {
        "https://creativecommons.org/licenses/by/4.0": "CC-BY-4.0",
        "http://creativecommons.org/licenses/by/4.0": "CC-BY-4.0",
        "https://creativecommons.org/publicdomain/zero/1.0": "CC0-1.0",
        "http://creativecommons.org/publicdomain/zero/1.0": "CC0-1.0",
    }
    return expressions.get(normalized_url, text or None)


def _front_matter(document: ParsedTextDocument) -> Mapping[str, object]:
    if document.format_id != "markdown":
        return {}
    block = next(
        (block for block in document.blocks if block.role == "front-matter"), None
    )
    if block is None:
        return {}
    if len(block.text.encode("utf-8")) > 64 * 1024:
        return {}
    lines = block.text.splitlines()
    if (
        len(lines) < 3
        or lines[0].strip() != "---"
        or lines[-1].strip()
        not in {
            "---",
            "...",
        }
    ):
        return {}
    supported = {
        "author",
        "authors",
        "canonical_uri",
        "canonical_url",
        "date",
        "doi",
        "journal",
        "language",
        "license",
        "license_url",
        "publication_date",
        "title",
    }
    values: dict[str, object] = {}
    for line in lines[1:-1]:
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        name, separator, raw_value = line.partition(":")
        name = name.strip().casefold()
        raw_value = raw_value.strip()
        if separator and name in supported and raw_value and len(raw_value) <= 4096:
            with suppress(yaml.YAMLError, RecursionError):
                values[name] = yaml.safe_load(raw_value)
    return values


def _jats_values(document: ParsedDocument) -> dict[str, object]:
    metadata = document.metadata
    return {
        "authors": metadata.authors,
        "doi": metadata.doi,
        "journal": metadata.journal,
        "language": metadata.language,
        "license_expression": _license_expression(
            metadata.license_text, metadata.license_url
        ),
        "license_url": metadata.license_url,
        "publication_date": str(metadata.publication_year),
        "title": metadata.title,
    }


def _html_values(document: ParsedHtmlDocument) -> dict[str, object]:
    metadata = document.metadata
    return {
        "authors": metadata.authors,
        "canonical_uri": metadata.canonical_url,
        "doi": metadata.doi,
        "journal": _first(
            metadata.raw_meta, "citation_journal_title", "citation_journal"
        ),
        "language": metadata.language or _first(metadata.raw_meta, "citation_language"),
        "license_expression": _first(
            metadata.raw_meta, "citation_license", "dc.rights"
        ),
        "license_url": _first(metadata.raw_meta, "citation_license_url"),
        "publication_date": _first(
            metadata.raw_meta, "citation_publication_date", "citation_date"
        ),
        "title": metadata.title,
    }


def _pdf_values(document: ParsedPdfDocument) -> dict[str, object]:
    metadata = document.metadata
    return {
        "authors": _authors(metadata.author),
        "publication_date": metadata.created_at,
        "title": metadata.title,
    }


def _docx_values(document: ParsedDocxDocument) -> dict[str, object]:
    metadata = document.metadata
    return {
        "authors": _authors(metadata.creator),
        "publication_date": metadata.created_at,
        "title": _first_block_title(document),
    }


def _text_values(document: ParsedTextDocument) -> dict[str, object]:
    values = _front_matter(document)
    license_value = values.get("license")
    license_mapping = license_value if isinstance(license_value, Mapping) else {}
    license_url = _optional_text(license_mapping.get("url", values.get("license_url")))
    license_text = _optional_text(license_mapping.get("expression", license_value))
    return {
        "authors": _authors(values.get("authors", values.get("author"))),
        "canonical_uri": _optional_text(
            values.get("canonical_uri", values.get("canonical_url"))
        ),
        "doi": _optional_text(values.get("doi")),
        "journal": _optional_text(values.get("journal")),
        "language": _optional_text(values.get("language")),
        "license_expression": _license_expression(license_text, license_url),
        "license_url": license_url,
        "publication_date": _optional_text(
            values.get("publication_date", values.get("date"))
        ),
        "title": _optional_text(values.get("title")) or _first_block_title(document),
    }


def metadata_record_from_parsed_document(
    document: ParsedSourceDocument,
    *,
    source_byte_length: int,
) -> SourceMetadataRecord:
    """Return one identity-bound typed record for any supported parser output."""

    if source_byte_length < 0:
        raise ValueError("parsed metadata source length must not be negative")
    if isinstance(document, ParsedDocument):
        values = _jats_values(document)
    elif isinstance(document, ParsedHtmlDocument):
        values = _html_values(document)
    elif isinstance(document, ParsedPdfDocument):
        values = _pdf_values(document)
    elif isinstance(document, ParsedDocxDocument):
        values = _docx_values(document)
    else:
        values = _text_values(document)
    manifest = document.manifest()
    return SourceMetadataRecord(
        provenance=(
            f"parser:{document.parser_name}:{document.parser_version}:"
            f"{manifest['manifest_sha256']}"
        ),
        doi=cast(str | None, values.get("doi")),
        canonical_uri=cast(str | None, values.get("canonical_uri")),
        authors=cast(tuple[str, ...], values.get("authors", ())),
        publication_date=cast(str | None, values.get("publication_date")),
        title=cast(str | None, values.get("title")),
        journal=cast(str | None, values.get("journal")),
        language=cast(str | None, values.get("language")),
        license_expression=cast(str | None, values.get("license_expression")),
        license_url=cast(str | None, values.get("license_url")),
        source="embedded_parser",
        source_format=_format_id(document),
        source_content_sha256=document.source_content_sha256,
        source_byte_length=source_byte_length,
    )


__all__ = ["metadata_record_from_parsed_document"]
