# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable document extraction values with source-resolving identities."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Literal, get_args

BlockRole = Literal[
    "title",
    "abstract",
    "section-heading",
    "paragraph",
    "caption",
    "table",
    "reference",
]
DocumentParseIssueCode = Literal[
    "format_mismatch",
    "encrypted_document",
    "invalid_locator",
    "malformed_document",
    "missing_required_metadata",
    "ocr_required",
    "source_changed",
    "source_not_admitted",
    "unsafe_markup",
]
LocatorValue = str | int

_BLOCK_ROLES = frozenset(get_args(BlockRole))
_PARSE_ISSUE_CODES = frozenset(get_args(DocumentParseIssueCode))
PdfPageExtraction = Literal["digital-text", "ocr-required"]
_PDF_PAGE_EXTRACTIONS = frozenset(get_args(PdfPageExtraction))
HtmlBlockRole = Literal[
    "title",
    "abstract",
    "section-heading",
    "paragraph",
    "list-item",
    "table",
]
_HTML_BLOCK_ROLES = frozenset(get_args(HtmlBlockRole))
TextBlockRole = Literal[
    "title",
    "front-matter",
    "heading",
    "section-heading",
    "paragraph",
    "list-item",
    "table-row",
    "code-block",
    "block-quote",
    "link",
    "syntax-example",
    "reference",
    "comment",
]
TextEncoding = Literal["utf-8", "utf-8-sig"]
NewlineStyle = Literal["none", "lf", "crlf", "cr", "mixed"]
_TEXT_BLOCK_ROLES = frozenset(get_args(TextBlockRole))
_TEXT_ENCODINGS = frozenset(get_args(TextEncoding))
_NEWLINE_STYLES = frozenset(get_args(NewlineStyle))
DocxBlockRole = Literal[
    "title",
    "heading",
    "paragraph",
    "list-item",
    "table-cell",
    "hyperlink",
    "footnote",
]
_DOCX_BLOCK_ROLES = frozenset(get_args(DocxBlockRole))


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """A stable locator scheme and its ordered, typed selectors."""

    scheme: str
    selectors: tuple[tuple[str, LocatorValue], ...]

    def __post_init__(self) -> None:
        if not self.scheme:
            raise ValueError("SourceLocator.scheme must not be empty")
        names = [name for name, _ in self.selectors]
        if (
            not names
            or any(not name for name in names)
            or len(names) != len(set(names))
        ):
            raise ValueError("SourceLocator selectors must have unique non-empty names")

    def get(self, name: str) -> LocatorValue | None:
        """Return one selector value when present."""

        return next((value for key, value in self.selectors if key == name), None)

    def manifest(self) -> dict[str, object]:
        """Return a JSON-safe locator representation."""

        return {
            "scheme": self.scheme,
            "selectors": dict(self.selectors),
        }


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Bibliographic metadata extracted from an immutable document."""

    title: str
    authors: tuple[str, ...]
    doi: str
    journal: str
    publication_year: int
    license_text: str
    license_url: str | None
    language: str | None

    def __post_init__(self) -> None:
        required = {
            "title": self.title,
            "doi": self.doi,
            "journal": self.journal,
            "license_text": self.license_text,
        }
        missing = [name for name, value in required.items() if not value]
        if missing or not self.authors or self.publication_year <= 0:
            raise ValueError(
                "DocumentMetadata requires complete bibliographic metadata"
            )

    def manifest(self) -> dict[str, object]:
        """Return the canonical bibliographic fields."""

        return {
            "authors": list(self.authors),
            "doi": self.doi,
            "journal": self.journal,
            "language": self.language,
            "license_text": self.license_text,
            "license_url": self.license_url,
            "publication_year": self.publication_year,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class ParsedBlock:
    """One ordered semantic block resolvable to an immutable source element."""

    index: int
    role: BlockRole
    text: str
    source_text: str
    locator: SourceLocator
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("ParsedBlock.index must not be negative")
        if self.role not in _BLOCK_ROLES:
            raise ValueError("unsupported parsed block role")
        if not self.text:
            raise ValueError("ParsedBlock.text must not be empty")

    @property
    def text_sha256(self) -> str:
        """Return the normalized block text digest."""

        return _text_sha256(self.text)

    @property
    def source_text_sha256(self) -> str:
        """Return the exact XML text-node sequence digest."""

        return _text_sha256(self.source_text)

    def manifest(self) -> dict[str, object]:
        """Return the source-resolving canonical block representation."""

        return {
            "index": self.index,
            "locator": self.locator.manifest(),
            "role": self.role,
            "section_path": list(self.section_path),
            "source_text": self.source_text,
            "source_text_sha256": self.source_text_sha256,
            "text": self.text,
            "text_sha256": self.text_sha256,
        }


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """A deterministic semantic extraction bound to one source content hash."""

    format_id: str
    source_content_sha256: str
    parser_name: str
    parser_version: str
    metadata: DocumentMetadata
    blocks: tuple[ParsedBlock, ...]

    def __post_init__(self) -> None:
        if not self.format_id or not self.parser_name or not self.parser_version:
            raise ValueError("ParsedDocument parser identity must be complete")
        if len(self.source_content_sha256) != 64:
            raise ValueError("ParsedDocument source hash must be a SHA-256 digest")
        if not self.blocks or tuple(block.index for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError("ParsedDocument blocks must use contiguous source order")

    def manifest(self) -> dict[str, object]:
        """Return a canonical extraction manifest and its identity."""

        payload: dict[str, object] = {
            "blocks": [block.manifest() for block in self.blocks],
            "format_id": self.format_id,
            "metadata": self.metadata.manifest(),
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "schema_version": "bijux.canon.ingest.parsed_document.v1",
            "source_content_sha256": self.source_content_sha256,
        }
        return {"manifest_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class PdfDocumentMetadata:
    """Standard PDF information fields preserved without inferred values."""

    title: str | None
    author: str | None
    subject: str | None
    keywords: str | None
    creator: str | None
    producer: str | None
    created_at: str | None
    modified_at: str | None
    raw_fields: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        names = [name for name, _ in self.raw_fields]
        if len(names) != len(set(names)):
            raise ValueError("PdfDocumentMetadata.raw_fields must have unique names")

    def manifest(self) -> dict[str, object]:
        """Return embedded metadata without supplementing missing fields."""

        return {
            "author": self.author,
            "created_at": self.created_at,
            "creator": self.creator,
            "keywords": self.keywords,
            "modified_at": self.modified_at,
            "producer": self.producer,
            "raw_fields": dict(self.raw_fields),
            "subject": self.subject,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class PdfPage:
    """Exact extracted page text with page geometry and character lineage."""

    page_number: int
    text: str
    width_points: float
    height_points: float
    rotation_degrees: int
    extraction_method: PdfPageExtraction
    locator: SourceLocator

    def __post_init__(self) -> None:
        if self.page_number <= 0:
            raise ValueError("PdfPage.page_number must be positive")
        if (
            not math.isfinite(self.width_points)
            or not math.isfinite(self.height_points)
            or self.width_points <= 0
            or self.height_points <= 0
        ):
            raise ValueError("PdfPage geometry must be positive and finite")
        if self.extraction_method not in _PDF_PAGE_EXTRACTIONS:
            raise ValueError("unsupported PDF page extraction method")
        if self.extraction_method == "digital-text" and not self.text.strip():
            raise ValueError("digital-text pages must contain extractable text")
        if self.extraction_method == "ocr-required" and self.text.strip():
            raise ValueError("ocr-required pages must not claim extracted text")

    @property
    def text_sha256(self) -> str:
        """Return the exact extracted page text digest."""

        return _text_sha256(self.text)

    def manifest(self) -> dict[str, object]:
        """Return exact page text, geometry, status, and locator."""

        return {
            "extraction_method": self.extraction_method,
            "height_points": self.height_points,
            "locator": self.locator.manifest(),
            "page_number": self.page_number,
            "rotation_degrees": self.rotation_degrees,
            "text": self.text,
            "text_sha256": self.text_sha256,
            "width_points": self.width_points,
        }


@dataclass(frozen=True, slots=True)
class ParsedPdfDocument:
    """A deterministic digital-PDF extraction bound to immutable source bytes."""

    source_content_sha256: str
    parser_name: str
    parser_version: str
    extractor: str
    metadata: PdfDocumentMetadata
    pages: tuple[PdfPage, ...]

    def __post_init__(self) -> None:
        if not self.parser_name or not self.parser_version or not self.extractor:
            raise ValueError("ParsedPdfDocument parser identity must be complete")
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("ParsedPdfDocument source hash must be lowercase SHA-256")
        if not self.pages or tuple(page.page_number for page in self.pages) != tuple(
            range(1, len(self.pages) + 1)
        ):
            raise ValueError(
                "ParsedPdfDocument pages must use contiguous one-based order"
            )

    def resolve_text(self, locator: SourceLocator) -> str:
        """Resolve and integrity-check one exact page character span."""

        if locator.scheme != "pdf-page-text-span":
            raise DocumentParseError(
                "invalid_locator", "locator scheme is not pdf-page-text-span"
            )
        extractor = locator.get("extractor")
        page_number = locator.get("page_number")
        page_sha256 = locator.get("page_text_sha256")
        text_start = locator.get("text_start")
        text_end = locator.get("text_end")
        if (
            extractor != self.extractor
            or isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or not isinstance(page_sha256, str)
            or isinstance(text_start, bool)
            or not isinstance(text_start, int)
            or isinstance(text_end, bool)
            or not isinstance(text_end, int)
            or page_number <= 0
            or page_number > len(self.pages)
        ):
            raise DocumentParseError(
                "invalid_locator", "PDF locator selectors do not match this extraction"
            )
        page = self.pages[page_number - 1]
        if page.text_sha256 != page_sha256:
            raise DocumentParseError(
                "invalid_locator", "PDF locator page text identity does not match"
            )
        if text_start < 0 or text_end < text_start or text_end > len(page.text):
            raise DocumentParseError(
                "invalid_locator", "PDF locator character span is out of bounds"
            )
        return page.text[text_start:text_end]

    def manifest(self) -> dict[str, object]:
        """Return a canonical PDF extraction manifest and its identity."""

        payload: dict[str, object] = {
            "extractor": self.extractor,
            "format_id": "pdf-digital",
            "metadata": self.metadata.manifest(),
            "pages": [page.manifest() for page in self.pages],
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "schema_version": "bijux.canon.ingest.parsed_pdf_document.v1",
            "source_content_sha256": self.source_content_sha256,
        }
        return {"manifest_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class HtmlLink:
    """One preserved hyperlink with its original DOM identity."""

    text: str
    href: str
    title: str | None
    locator: SourceLocator

    def __post_init__(self) -> None:
        if not self.href:
            raise ValueError("HtmlLink.href must not be empty")

    def manifest(self) -> dict[str, object]:
        """Return the preserved link representation."""

        return {
            "href": self.href,
            "locator": self.locator.manifest(),
            "text": self.text,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class HtmlDocumentMetadata:
    """Citation and document metadata preserved from HTML markup."""

    title: str
    authors: tuple[str, ...]
    doi: str
    language: str | None
    canonical_url: str | None
    raw_meta: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.title or not self.authors or not self.doi:
            raise ValueError("HtmlDocumentMetadata requires title, authors, and DOI")

    def manifest(self) -> dict[str, object]:
        """Return citation metadata without discarding repeated fields."""

        return {
            "authors": list(self.authors),
            "canonical_url": self.canonical_url,
            "doi": self.doi,
            "language": self.language,
            "raw_meta": [list(item) for item in self.raw_meta],
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class ParsedHtmlBlock:
    """One ordered semantic HTML block with stable DOM lineage."""

    index: int
    role: HtmlBlockRole
    text: str
    source_text: str
    locator: SourceLocator
    section_path: tuple[str, ...] = ()
    links: tuple[HtmlLink, ...] = ()

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("ParsedHtmlBlock.index must not be negative")
        if self.role not in _HTML_BLOCK_ROLES:
            raise ValueError("unsupported HTML block role")
        if not self.text:
            raise ValueError("ParsedHtmlBlock.text must not be empty")

    @property
    def text_sha256(self) -> str:
        """Return the normalized block text digest."""

        return _text_sha256(self.text)

    @property
    def source_text_sha256(self) -> str:
        """Return the exact HTML text-node sequence digest."""

        return _text_sha256(self.source_text)

    def manifest(self) -> dict[str, object]:
        """Return the source-resolving block representation."""

        return {
            "index": self.index,
            "links": [link.manifest() for link in self.links],
            "locator": self.locator.manifest(),
            "role": self.role,
            "section_path": list(self.section_path),
            "source_text": self.source_text,
            "source_text_sha256": self.source_text_sha256,
            "text": self.text,
            "text_sha256": self.text_sha256,
        }


@dataclass(frozen=True, slots=True)
class ParsedHtmlDocument:
    """A deterministic semantic HTML extraction bound to source bytes."""

    source_content_sha256: str
    parser_name: str
    parser_version: str
    metadata: HtmlDocumentMetadata
    blocks: tuple[ParsedHtmlBlock, ...]

    def __post_init__(self) -> None:
        if not self.parser_name or not self.parser_version:
            raise ValueError("ParsedHtmlDocument parser identity must be complete")
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("ParsedHtmlDocument source hash must be lowercase SHA-256")
        if not self.blocks or tuple(block.index for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError(
                "ParsedHtmlDocument blocks must use contiguous source order"
            )

    def manifest(self) -> dict[str, object]:
        """Return a canonical HTML extraction manifest and its identity."""

        payload: dict[str, object] = {
            "blocks": [block.manifest() for block in self.blocks],
            "format_id": "html",
            "metadata": self.metadata.manifest(),
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "schema_version": "bijux.canon.ingest.parsed_html_document.v1",
            "source_content_sha256": self.source_content_sha256,
        }
        return {"manifest_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class ParsedTextBlock:
    """One exact line-oriented block with normalized character lineage."""

    index: int
    role: TextBlockRole
    text: str
    locator: SourceLocator
    section_path: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("ParsedTextBlock.index must not be negative")
        if self.role not in _TEXT_BLOCK_ROLES:
            raise ValueError("unsupported text block role")
        if not self.text:
            raise ValueError("ParsedTextBlock.text must not be empty")

    @property
    def text_sha256(self) -> str:
        """Return the exact normalized-source block digest."""

        return _text_sha256(self.text)

    def manifest(self) -> dict[str, object]:
        """Return the exact line and character span representation."""

        return {
            "index": self.index,
            "locator": self.locator.manifest(),
            "role": self.role,
            "section_path": list(self.section_path),
            "text": self.text,
            "text_sha256": self.text_sha256,
        }


@dataclass(frozen=True, slots=True)
class ParsedTextDocument:
    """A deterministic Markdown or plain-text extraction bound to source bytes."""

    format_id: Literal["markdown", "text"]
    source_content_sha256: str
    parser_name: str
    parser_version: str
    encoding: TextEncoding
    newline_style: NewlineStyle
    normalized_text: str
    blocks: tuple[ParsedTextBlock, ...]

    def __post_init__(self) -> None:
        if self.format_id not in {"markdown", "text"}:
            raise ValueError("ParsedTextDocument format must be markdown or text")
        if not self.parser_name or not self.parser_version:
            raise ValueError("ParsedTextDocument parser identity must be complete")
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("ParsedTextDocument source hash must be lowercase SHA-256")
        if self.encoding not in _TEXT_ENCODINGS:
            raise ValueError("unsupported text encoding")
        if self.newline_style not in _NEWLINE_STYLES:
            raise ValueError("unsupported newline style")
        if not self.normalized_text:
            raise ValueError("ParsedTextDocument normalized text must not be empty")
        if not self.blocks or tuple(block.index for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError(
                "ParsedTextDocument blocks must use contiguous source order"
            )

    @property
    def normalized_text_sha256(self) -> str:
        """Return the normalized full-text identity used by every locator."""

        return _text_sha256(self.normalized_text)

    def resolve_text(self, locator: SourceLocator) -> str:
        """Resolve and integrity-check an exact normalized character span."""

        if locator.scheme != f"{self.format_id}-line-span":
            raise DocumentParseError(
                "invalid_locator", "locator scheme does not match text format"
            )
        source_sha256 = locator.get("normalized_text_sha256")
        line_start = locator.get("line_start")
        line_end = locator.get("line_end")
        char_start = locator.get("char_start")
        char_end = locator.get("char_end")
        if (
            source_sha256 != self.normalized_text_sha256
            or isinstance(line_start, bool)
            or not isinstance(line_start, int)
            or isinstance(line_end, bool)
            or not isinstance(line_end, int)
            or isinstance(char_start, bool)
            or not isinstance(char_start, int)
            or isinstance(char_end, bool)
            or not isinstance(char_end, int)
            or char_start < 0
            or char_end < char_start
            or char_end > len(self.normalized_text)
        ):
            raise DocumentParseError(
                "invalid_locator", "text locator character span is invalid or stale"
            )
        resolved_line_start = self.normalized_text.count("\n", 0, char_start) + 1
        resolved_line_end = self.normalized_text.count("\n", 0, char_end) + 1
        if line_start != resolved_line_start or line_end != resolved_line_end:
            raise DocumentParseError(
                "invalid_locator", "text locator line and character spans disagree"
            )
        return self.normalized_text[char_start:char_end]

    def manifest(self) -> dict[str, object]:
        """Return a canonical line-oriented extraction manifest and identity."""

        payload: dict[str, object] = {
            "blocks": [block.manifest() for block in self.blocks],
            "encoding": self.encoding,
            "format_id": self.format_id,
            "newline_style": self.newline_style,
            "normalized_text_sha256": self.normalized_text_sha256,
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "schema_version": "bijux.canon.ingest.parsed_text_document.v1",
            "source_content_sha256": self.source_content_sha256,
        }
        return {"manifest_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class DocxDocumentMetadata:
    """Core OOXML document properties preserved without inferred values."""

    creator: str | None
    last_modified_by: str | None
    created_at: str | None
    modified_at: str | None
    revision: str | None
    raw_fields: tuple[tuple[str, str], ...]

    def manifest(self) -> dict[str, object]:
        """Return the core property values and their original field names."""

        return {
            "created_at": self.created_at,
            "creator": self.creator,
            "last_modified_by": self.last_modified_by,
            "modified_at": self.modified_at,
            "raw_fields": dict(self.raw_fields),
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class ParsedDocxBlock:
    """One semantic OOXML block with package-part lineage."""

    index: int
    role: DocxBlockRole
    text: str
    locator: SourceLocator
    section_path: tuple[str, ...] = ()
    target: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0 or self.role not in _DOCX_BLOCK_ROLES or not self.text:
            raise ValueError("ParsedDocxBlock requires a valid index, role, and text")

    @property
    def text_sha256(self) -> str:
        """Return the normalized OOXML text digest."""

        return _text_sha256(self.text)

    def manifest(self) -> dict[str, object]:
        """Return the source-resolving OOXML block representation."""

        return {
            "index": self.index,
            "locator": self.locator.manifest(),
            "role": self.role,
            "section_path": list(self.section_path),
            "target": self.target,
            "text": self.text,
            "text_sha256": self.text_sha256,
        }


@dataclass(frozen=True, slots=True)
class ParsedDocxDocument:
    """A deterministic DOCX extraction bound to immutable package bytes."""

    source_content_sha256: str
    parser_name: str
    parser_version: str
    metadata: DocxDocumentMetadata
    blocks: tuple[ParsedDocxBlock, ...]

    def __post_init__(self) -> None:
        if not self.parser_name or not self.parser_version:
            raise ValueError("ParsedDocxDocument parser identity must be complete")
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("ParsedDocxDocument source hash must be lowercase SHA-256")
        if not self.blocks or tuple(block.index for block in self.blocks) != tuple(
            range(len(self.blocks))
        ):
            raise ValueError(
                "ParsedDocxDocument blocks must use contiguous source order"
            )

    def manifest(self) -> dict[str, object]:
        """Return a canonical DOCX extraction manifest and its identity."""

        payload: dict[str, object] = {
            "blocks": [block.manifest() for block in self.blocks],
            "format_id": "docx",
            "metadata": self.metadata.manifest(),
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "schema_version": "bijux.canon.ingest.parsed_docx_document.v1",
            "source_content_sha256": self.source_content_sha256,
        }
        return {"manifest_sha256": _identity(payload), **payload}


class DocumentParseError(ValueError):
    """A typed refusal at the semantic document parsing boundary."""

    def __init__(self, code: DocumentParseIssueCode, detail: str) -> None:
        if code not in _PARSE_ISSUE_CODES:
            raise ValueError("unsupported document parse issue code")
        if not detail:
            raise ValueError("DocumentParseError.detail must not be empty")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


__all__ = [
    "BlockRole",
    "DocumentMetadata",
    "DocumentParseError",
    "DocumentParseIssueCode",
    "DocxBlockRole",
    "DocxDocumentMetadata",
    "ParsedBlock",
    "ParsedDocxBlock",
    "ParsedDocxDocument",
    "ParsedDocument",
    "ParsedHtmlBlock",
    "ParsedHtmlDocument",
    "ParsedPdfDocument",
    "HtmlBlockRole",
    "HtmlDocumentMetadata",
    "HtmlLink",
    "NewlineStyle",
    "ParsedTextBlock",
    "ParsedTextDocument",
    "PdfDocumentMetadata",
    "PdfPage",
    "PdfPageExtraction",
    "SourceLocator",
    "TextBlockRole",
    "TextEncoding",
]
