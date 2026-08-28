# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application boundary for semantic extraction from admitted documents."""

from __future__ import annotations

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    OcrRequiredOutcome,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
)
from bijux_canon_ingest.domain.source_admission import AdmissionResult
from bijux_canon_ingest.infra.adapters.file_admission import read_current_source
from bijux_canon_ingest.infra.admission.limits import AdmissionFailure
from bijux_canon_ingest.infra.parsers.docx import parse_docx_content
from bijux_canon_ingest.infra.parsers.html import parse_html_content
from bijux_canon_ingest.infra.parsers.jats import parse_jats_content
from bijux_canon_ingest.infra.parsers.ocr import (
    image_ocr_requirement,
    pdf_ocr_requirement,
)
from bijux_canon_ingest.infra.parsers.pdf import parse_pdf_content
from bijux_canon_ingest.infra.parsers.text import (
    parse_markdown_content,
    parse_text_content,
)


def parse_jats(admission: AdmissionResult) -> ParsedDocument:
    """Parse one immutable source admitted specifically as JATS."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before JATS parsing"
        )
    if admission.format_id != "jats":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not JATS"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_jats_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def parse_pdf(admission: AdmissionResult) -> ParsedPdfDocument:
    """Parse one immutable source admitted specifically as a digital PDF."""

    if not admission.admitted:
        if any(issue.code == "encrypted_input" for issue in admission.issues):
            raise DocumentParseError(
                "encrypted_document", "encrypted PDF input cannot be extracted"
            )
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before PDF parsing"
        )
    if admission.format_id != "pdf-digital":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not a digital PDF"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_pdf_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def parse_html(admission: AdmissionResult) -> ParsedHtmlDocument:
    """Parse one immutable source admitted specifically as HTML."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before HTML parsing"
        )
    if admission.format_id != "html":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not HTML"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_html_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def parse_markdown(admission: AdmissionResult) -> ParsedTextDocument:
    """Parse one immutable source admitted specifically as Markdown."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before Markdown parsing"
        )
    if admission.format_id != "markdown":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not Markdown"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_markdown_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def parse_text(admission: AdmissionResult) -> ParsedTextDocument:
    """Parse one immutable source admitted specifically as plain text."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before text parsing"
        )
    if admission.format_id != "text":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not plain text"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_text_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def parse_docx(admission: AdmissionResult) -> ParsedDocxDocument:
    """Parse one immutable source admitted specifically as DOCX."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before DOCX parsing"
        )
    if admission.format_id != "docx":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not DOCX"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_docx_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


def assess_ocr_requirement(admission: AdmissionResult) -> OcrRequiredOutcome:
    """Return typed evidence without performing OCR."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before OCR assessment"
        )
    if admission.format_id not in {"ocr-required", "pdf-digital"}:
        raise DocumentParseError(
            "format_mismatch", "admitted source is not an OCR candidate"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    if admission.format_id == "pdf-digital":
        return pdf_ocr_requirement(
            content, source_content_sha256=admission.source.content_sha256
        )
    return image_ocr_requirement(
        content,
        source_content_sha256=admission.source.content_sha256,
        media_type=admission.evidence.detected_media_type
        or admission.source.media_type,
    )


__all__ = [
    "assess_ocr_requirement",
    "parse_docx",
    "parse_html",
    "parse_jats",
    "parse_markdown",
    "parse_pdf",
    "parse_text",
]
