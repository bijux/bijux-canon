# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Hashed source-to-document-to-mapping-to-chunk citation lineage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_ingest.domain.document_extraction import (
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    SourceLocator,
)
from bijux_canon_ingest.domain.semantic_chunking import SemanticChunk
from bijux_canon_ingest.domain.source_mapping import SourceByteSpan

ParsedSourceDocument = (
    ParsedDocument
    | ParsedDocxDocument
    | ParsedHtmlDocument
    | ParsedPdfDocument
    | ParsedTextDocument
)


class CitationLineageErrorCode(StrEnum):
    """Stable refusal reasons for an unverifiable citation lineage."""

    chunk_unavailable = "chunk_unavailable"
    document_identity_mismatch = "document_identity_mismatch"
    locator_ambiguous = "locator_ambiguous"
    locator_unavailable = "locator_unavailable"
    mapping_identity_mismatch = "mapping_identity_mismatch"
    parser_identity_mismatch = "parser_identity_mismatch"
    source_identity_mismatch = "source_identity_mismatch"
    text_identity_mismatch = "text_identity_mismatch"


class CitationLineageError(ValueError):
    """A citation cannot be resolved through its immutable ingest lineage."""

    def __init__(self, code: CitationLineageErrorCode, detail: str) -> None:
        if not detail:
            raise ValueError("citation lineage error detail must not be empty")
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


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


def _is_artifact_id(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


@dataclass(frozen=True, slots=True)
class CitationLineageSegment:
    """One chunk span linked through one normalized mapping and source locator."""

    source_content_sha256: str
    document_id: str
    parser_manifest_sha256: str
    chunk_id: str
    mapping_sha256: str
    parent_mapping_sha256: str | None
    locator: SourceLocator
    source_span: SourceByteSpan
    chunk_start: int
    chunk_end: int
    normalized_start: int
    normalized_end: int
    normalized_text: str
    original_text_sha256: str

    def __post_init__(self) -> None:
        identities = (
            self.document_id,
            self.parser_manifest_sha256,
            self.chunk_id,
            self.mapping_sha256,
        )
        if not _is_sha256(self.source_content_sha256) or any(
            not _is_artifact_id(value) for value in identities
        ):
            raise ValueError("citation lineage segment identities are invalid")
        if self.parent_mapping_sha256 is not None and not _is_artifact_id(
            self.parent_mapping_sha256
        ):
            raise ValueError("citation lineage parent mapping identity is invalid")
        if (
            self.chunk_start < 0
            or self.chunk_end <= self.chunk_start
            or self.normalized_start < 0
            or self.normalized_end <= self.normalized_start
            or self.chunk_end - self.chunk_start != len(self.normalized_text)
            or self.normalized_end - self.normalized_start != len(self.normalized_text)
            or not self.normalized_text
            or not _is_sha256(self.original_text_sha256)
        ):
            raise ValueError("citation lineage segment spans or text are invalid")
        if self.source_span.selected_bytes_sha256 != self.source_content_sha256:
            raise ValueError("citation lineage segment source span is not source-bound")

    @property
    def normalized_text_sha256(self) -> str:
        return _text_sha256(self.normalized_text)

    @property
    def locator_sha256(self) -> str:
        return _identity(self.locator.manifest())

    @property
    def source_document_edge_sha256(self) -> str:
        return _identity(
            {
                "document_id": self.document_id,
                "parser_manifest_sha256": self.parser_manifest_sha256,
                "source_content_sha256": self.source_content_sha256,
            }
        )

    @property
    def document_mapping_edge_sha256(self) -> str:
        return _identity(
            {
                "document_id": self.document_id,
                "locator_sha256": self.locator_sha256,
                "mapping_sha256": self.mapping_sha256,
                "parser_manifest_sha256": self.parser_manifest_sha256,
            }
        )

    @property
    def mapping_chunk_edge_sha256(self) -> str:
        return _identity(
            {
                "chunk_character_span": {
                    "end": self.chunk_end,
                    "start": self.chunk_start,
                },
                "chunk_id": self.chunk_id,
                "mapping_sha256": self.mapping_sha256,
                "normalized_text_sha256": self.normalized_text_sha256,
            }
        )

    @property
    def segment_sha256(self) -> str:
        return _identity(self._payload())

    def _payload(self) -> dict[str, object]:
        return {
            "chunk_character_span": {
                "coordinate_system": "unicode_code_point",
                "end": self.chunk_end,
                "start": self.chunk_start,
            },
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_mapping_edge_sha256": self.document_mapping_edge_sha256,
            "locator": self.locator.manifest(),
            "locator_sha256": self.locator_sha256,
            "mapping_chunk_edge_sha256": self.mapping_chunk_edge_sha256,
            "mapping_sha256": self.mapping_sha256,
            "normalized_character_span": {
                "coordinate_system": "unicode_code_point",
                "end": self.normalized_end,
                "start": self.normalized_start,
            },
            "normalized_text_sha256": self.normalized_text_sha256,
            "original_text_sha256": self.original_text_sha256,
            "parent_mapping_sha256": self.parent_mapping_sha256,
            "parser_manifest_sha256": self.parser_manifest_sha256,
            "schema_version": "bijux.canon.ingest.citation_lineage_segment.v1",
            "source_content_sha256": self.source_content_sha256,
            "source_document_edge_sha256": self.source_document_edge_sha256,
            "source_span": self.source_span.manifest(),
        }

    def manifest(self) -> dict[str, object]:
        """Return this segment and all three hashed lineage edges."""

        payload = self._payload()
        return {"segment_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class CitationLineageRecord:
    """Complete exact-text and locator lineage for one semantic chunk."""

    chunk_id: str
    document_id: str
    chunk_index: int
    normalized_text: str
    section_paths: tuple[tuple[str, ...], ...]
    segments: tuple[CitationLineageSegment, ...]

    def __post_init__(self) -> None:
        if (
            not _is_artifact_id(self.chunk_id)
            or not _is_artifact_id(self.document_id)
            or self.chunk_index < 0
            or not self.normalized_text
            or not self.segments
        ):
            raise ValueError("citation lineage record identity or text is invalid")
        if any(
            segment.chunk_id != self.chunk_id or segment.document_id != self.document_id
            for segment in self.segments
        ):
            raise ValueError("citation lineage record contains foreign segments")
        if tuple(segment.chunk_start for segment in self.segments) != tuple(
            sorted(segment.chunk_start for segment in self.segments)
        ):
            raise ValueError("citation lineage segments must use source order")
        if any(
            left.chunk_end > right.chunk_start
            for left, right in zip(self.segments, self.segments[1:], strict=False)
        ):
            raise ValueError("citation lineage segment spans must not overlap")
        if any(
            self.normalized_text[segment.chunk_start : segment.chunk_end]
            != segment.normalized_text
            for segment in self.segments
        ):
            raise ValueError("citation lineage segments do not resolve chunk text")
        if len(self.section_paths) != len(self.segments):
            raise ValueError("citation section paths must align with segments")

    @property
    def normalized_text_sha256(self) -> str:
        return _text_sha256(self.normalized_text)

    @property
    def record_sha256(self) -> str:
        return _identity(self._payload())

    def _payload(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "document_id": self.document_id,
            "normalized_text_sha256": self.normalized_text_sha256,
            "schema_version": "bijux.canon.ingest.citation_lineage_record.v1",
            "section_paths": [list(path) for path in self.section_paths],
            "segments": [segment.manifest() for segment in self.segments],
        }

    def manifest(self) -> dict[str, object]:
        """Return the exact chunk text plus its ordered source-locator edges."""

        payload = self._payload()
        return {"record_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class DocumentCitationLineage:
    """Parser-bound lineage graph for every chunk in one snapshot document."""

    document_id: str
    source_content_sha256: str
    parser_name: str
    parser_version: str
    parser_manifest_sha256: str
    records: tuple[CitationLineageRecord, ...]

    def __post_init__(self) -> None:
        if (
            not _is_artifact_id(self.document_id)
            or not _is_sha256(self.source_content_sha256)
            or not self.parser_name
            or not self.parser_version
            or not _is_artifact_id(self.parser_manifest_sha256)
            or not self.records
        ):
            raise ValueError("document citation lineage identity is invalid")
        if tuple(record.chunk_index for record in self.records) != tuple(
            range(len(self.records))
        ):
            raise ValueError("citation lineage records must use document chunk order")
        chunk_ids = tuple(record.chunk_id for record in self.records)
        if len(chunk_ids) != len(set(chunk_ids)) or any(
            record.document_id != self.document_id for record in self.records
        ):
            raise ValueError("document citation lineage chunk bindings are invalid")

    @property
    def lineage_sha256(self) -> str:
        return _identity(self._payload())

    def _payload(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "parser": {"name": self.parser_name, "version": self.parser_version},
            "parser_manifest_sha256": self.parser_manifest_sha256,
            "records": [record.manifest() for record in self.records],
            "schema_version": "bijux.canon.ingest.document_citation_lineage.v1",
            "source_content_sha256": self.source_content_sha256,
        }

    def manifest(self) -> dict[str, object]:
        """Return the canonical document lineage graph and its identity."""

        payload = self._payload()
        return {"lineage_sha256": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class ResolvedCitation:
    """An exact verified chunk span and every intersecting format locator."""

    chunk_id: str
    character_start: int
    character_end: int
    exact_text: str
    exact_text_sha256: str
    segments: tuple[CitationLineageSegment, ...]

    def manifest(self) -> dict[str, object]:
        """Return the verified text and source locator evidence."""

        return {
            "character_end": self.character_end,
            "character_start": self.character_start,
            "chunk_id": self.chunk_id,
            "exact_text": self.exact_text,
            "exact_text_sha256": self.exact_text_sha256,
            "schema_version": "bijux.canon.ingest.resolved_citation.v1",
            "segments": [segment.manifest() for segment in self.segments],
        }


def resolve_source_locator(
    document: ParsedSourceDocument,
    locator: SourceLocator,
) -> str:
    """Resolve a format locator without falling back to text search."""

    if isinstance(document, ParsedPdfDocument | ParsedTextDocument):
        try:
            return document.resolve_text(locator)
        except ValueError as error:
            raise CitationLineageError(
                CitationLineageErrorCode.locator_unavailable,
                "format locator does not resolve in the parsed document",
            ) from error
    if isinstance(document, ParsedDocument | ParsedHtmlDocument):
        resolved = tuple(
            block.source_text for block in document.blocks if block.locator == locator
        )
    else:
        resolved = tuple(
            block.text for block in document.blocks if block.locator == locator
        )
    if not resolved:
        raise CitationLineageError(
            CitationLineageErrorCode.locator_unavailable,
            "format locator is absent from the parsed document",
        )
    if len(resolved) != 1:
        raise CitationLineageError(
            CitationLineageErrorCode.locator_ambiguous,
            "format locator resolves to more than one parsed block",
        )
    return resolved[0]


def build_document_citation_lineage(
    *,
    document: ParsedSourceDocument,
    document_id: str,
    chunks: tuple[SemanticChunk, ...],
) -> DocumentCitationLineage:
    """Build and verify every hashed edge in one document citation graph."""

    parser_manifest_sha256 = str(document.manifest()["manifest_sha256"])
    records: list[CitationLineageRecord] = []
    for chunk in chunks:
        cursor = 0
        segments: list[CitationLineageSegment] = []
        for mapping in chunk.mappings:
            resolved = resolve_source_locator(document, mapping.locator)
            if _text_sha256(resolved) != mapping.original_text_sha256:
                raise CitationLineageError(
                    CitationLineageErrorCode.text_identity_mismatch,
                    "format locator text does not match its normalized mapping",
                )
            chunk_end = cursor + len(mapping.normalized_text)
            segments.append(
                CitationLineageSegment(
                    source_content_sha256=mapping.source_content_sha256,
                    document_id=document_id,
                    parser_manifest_sha256=parser_manifest_sha256,
                    chunk_id=chunk.chunk_id,
                    mapping_sha256=mapping.mapping_sha256,
                    parent_mapping_sha256=mapping.parent_mapping_sha256,
                    locator=mapping.locator,
                    source_span=mapping.source_span,
                    chunk_start=cursor,
                    chunk_end=chunk_end,
                    normalized_start=mapping.normalized_start,
                    normalized_end=mapping.normalized_end,
                    normalized_text=mapping.normalized_text,
                    original_text_sha256=mapping.original_text_sha256,
                )
            )
            cursor = chunk_end + len(chunk.block_separator)
        records.append(
            CitationLineageRecord(
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                normalized_text=chunk.normalized_text,
                section_paths=chunk.section_paths,
                segments=tuple(segments),
            )
        )
    return DocumentCitationLineage(
        document_id=document_id,
        source_content_sha256=document.source_content_sha256,
        parser_name=document.parser_name,
        parser_version=document.parser_version,
        parser_manifest_sha256=parser_manifest_sha256,
        records=tuple(records),
    )


def resolve_chunk_citation(
    *,
    lineage: DocumentCitationLineage,
    document: ParsedSourceDocument,
    chunks: tuple[SemanticChunk, ...],
    source_content: bytes,
    expected_document_id: str,
    chunk_id: str,
    character_start: int,
    character_end: int,
    expected_text_sha256: str,
) -> ResolvedCitation:
    """Resolve and verify an exact Unicode chunk span through immutable source."""

    if hashlib.sha256(source_content).hexdigest() != lineage.source_content_sha256:
        raise CitationLineageError(
            CitationLineageErrorCode.source_identity_mismatch,
            "source bytes do not match citation lineage",
        )
    if lineage.document_id != expected_document_id:
        raise CitationLineageError(
            CitationLineageErrorCode.document_identity_mismatch,
            "document identity does not match citation lineage",
        )
    if document.manifest()["manifest_sha256"] != lineage.parser_manifest_sha256:
        raise CitationLineageError(
            CitationLineageErrorCode.parser_identity_mismatch,
            "parsed document identity does not match citation lineage",
        )
    matches = tuple(record for record in lineage.records if record.chunk_id == chunk_id)
    if len(matches) != 1:
        raise CitationLineageError(
            CitationLineageErrorCode.chunk_unavailable,
            "chunk identity does not resolve exactly once in citation lineage",
        )
    record = matches[0]
    chunk_matches = tuple(chunk for chunk in chunks if chunk.chunk_id == chunk_id)
    if len(chunk_matches) != 1:
        raise CitationLineageError(
            CitationLineageErrorCode.chunk_unavailable,
            "chunk identity does not resolve exactly once in parsed chunks",
        )
    chunk = chunk_matches[0]
    if (
        record.chunk_index != chunk.chunk_index
        or record.normalized_text != chunk.normalized_text
        or record.normalized_text_sha256 != chunk.normalized_text_sha256
    ):
        raise CitationLineageError(
            CitationLineageErrorCode.text_identity_mismatch,
            "citation lineage record does not match the semantic chunk",
        )
    if tuple(segment.mapping_sha256 for segment in record.segments) != tuple(
        mapping.mapping_sha256 for mapping in chunk.mappings
    ) or any(
        (
            segment.locator != mapping.locator
            or segment.normalized_start != mapping.normalized_start
            or segment.normalized_end != mapping.normalized_end
            or segment.normalized_text_sha256 != mapping.normalized_text_sha256
            or segment.original_text_sha256 != mapping.original_text_sha256
        )
        for segment, mapping in zip(record.segments, chunk.mappings, strict=True)
    ):
        raise CitationLineageError(
            CitationLineageErrorCode.mapping_identity_mismatch,
            "citation lineage segments do not match semantic chunk mappings",
        )
    if (
        character_start < 0
        or character_end <= character_start
        or character_end > len(record.normalized_text)
    ):
        raise CitationLineageError(
            CitationLineageErrorCode.locator_unavailable,
            "citation character span is outside the chunk",
        )
    exact_text = record.normalized_text[character_start:character_end]
    if _text_sha256(exact_text) != expected_text_sha256:
        raise CitationLineageError(
            CitationLineageErrorCode.text_identity_mismatch,
            "citation text hash does not match the resolved chunk span",
        )
    selected_segments = tuple(
        segment
        for segment in record.segments
        if segment.chunk_start < character_end and character_start < segment.chunk_end
    )
    if not selected_segments:
        raise CitationLineageError(
            CitationLineageErrorCode.locator_unavailable,
            "citation span contains no source-resolving text",
        )
    for segment in selected_segments:
        segment.source_span.resolve(source_content)
        resolved = resolve_source_locator(document, segment.locator)
        if _text_sha256(resolved) != segment.original_text_sha256:
            raise CitationLineageError(
                CitationLineageErrorCode.text_identity_mismatch,
                "source locator text changed after lineage construction",
            )
    return ResolvedCitation(
        chunk_id=chunk_id,
        character_start=character_start,
        character_end=character_end,
        exact_text=exact_text,
        exact_text_sha256=expected_text_sha256,
        segments=selected_segments,
    )


__all__ = [
    "CitationLineageError",
    "CitationLineageErrorCode",
    "CitationLineageRecord",
    "CitationLineageSegment",
    "DocumentCitationLineage",
    "ResolvedCitation",
    "build_document_citation_lineage",
    "resolve_chunk_citation",
    "resolve_source_locator",
]
