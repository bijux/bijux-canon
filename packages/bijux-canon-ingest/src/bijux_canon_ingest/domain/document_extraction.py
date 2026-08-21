# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable document extraction values with source-resolving identities."""

from __future__ import annotations

import hashlib
import json
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
    "malformed_document",
    "missing_required_metadata",
    "source_changed",
    "source_not_admitted",
    "unsafe_markup",
]
LocatorValue = str | int

_BLOCK_ROLES = frozenset(get_args(BlockRole))
_PARSE_ISSUE_CODES = frozenset(get_args(DocumentParseIssueCode))


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
        if not names or any(not name for name in names) or len(names) != len(set(names)):
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
            raise ValueError("DocumentMetadata requires complete bibliographic metadata")

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
    "ParsedBlock",
    "ParsedDocument",
    "SourceLocator",
]
