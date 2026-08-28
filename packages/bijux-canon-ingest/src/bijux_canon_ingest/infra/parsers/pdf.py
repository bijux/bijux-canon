# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic page-text extraction from admitted digital PDFs."""

from __future__ import annotations

import hashlib
from io import BytesIO

import pypdf
from pypdf import PdfReader

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    ParsedPdfDocument,
    PdfDocumentMetadata,
    PdfPage,
    PdfPageExtraction,
    SourceLocator,
)

_PARSER_NAME = "pypdf"


def parser_identity() -> tuple[str, str, str]:
    """Return the extraction contract that governs digital-PDF reuse."""

    return _PARSER_NAME, pypdf.__version__, "bijux.canon.ingest.parsed_pdf_document.v1"


def _metadata(reader: PdfReader) -> PdfDocumentMetadata:
    embedded = reader.metadata
    raw_fields = tuple(
        sorted(
            (str(name), str(value))
            for name, value in (embedded or {}).items()
            if value is not None
        )
    )

    def value(name: str) -> str | None:
        raw = dict(raw_fields).get(name)
        return raw if raw else None

    return PdfDocumentMetadata(
        title=value("/Title"),
        author=value("/Author"),
        subject=value("/Subject"),
        keywords=value("/Keywords"),
        creator=value("/Creator"),
        producer=value("/Producer"),
        created_at=value("/CreationDate"),
        modified_at=value("/ModDate"),
        raw_fields=raw_fields,
    )


def parse_pdf_content(
    content: bytes, *, source_content_sha256: str
) -> ParsedPdfDocument:
    """Extract exact ordered page text from already-admitted PDF bytes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "PDF bytes do not match the admitted source identity"
        )
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise DocumentParseError(
                "encrypted_document", "encrypted PDF input cannot be extracted"
            )
        extractor = f"pypdf-{pypdf.__version__}-page-extract-text"
        pages: list[PdfPage] = []
        for page_number, source_page in enumerate(reader.pages, 1):
            text = source_page.extract_text() or ""
            page_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
            extraction_method: PdfPageExtraction = (
                "digital-text" if text.strip() else "ocr-required"
            )
            pages.append(
                PdfPage(
                    page_number=page_number,
                    text=text,
                    width_points=float(source_page.mediabox.width),
                    height_points=float(source_page.mediabox.height),
                    rotation_degrees=int(source_page.rotation),
                    extraction_method=extraction_method,
                    locator=SourceLocator(
                        scheme="pdf-page-text-span",
                        selectors=(
                            ("extractor", extractor),
                            ("page_number", page_number),
                            ("page_text_sha256", page_sha256),
                            ("text_start", 0),
                            ("text_end", len(text)),
                        ),
                    ),
                )
            )
        metadata = _metadata(reader)
    except DocumentParseError:
        raise
    except Exception as error:
        raise DocumentParseError(
            "malformed_document", "PDF structure or page text cannot be extracted"
        ) from error
    if not pages:
        raise DocumentParseError("malformed_document", "PDF has no pages")
    if all(page.extraction_method == "ocr-required" for page in pages):
        raise DocumentParseError(
            "ocr_required",
            "PDF contains no extractable digital text; OCR was not performed",
        )
    return ParsedPdfDocument(
        source_content_sha256=source_content_sha256,
        parser_name=_PARSER_NAME,
        parser_version=pypdf.__version__,
        extractor=extractor,
        metadata=metadata,
        pages=tuple(pages),
    )


__all__ = ["parse_pdf_content", "parser_identity"]
