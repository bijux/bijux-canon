# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Strict reconstruction of immutable snapshot members for restart reuse."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TypeVar, cast

from bijux_canon_ingest.domain.corpus_publication import PublishedCorpusSnapshot
from bijux_canon_ingest.domain.corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    SnapshotParsedDocument,
)
from bijux_canon_ingest.domain.document_extraction import (
    DocumentMetadata,
    DocxDocumentMetadata,
    HtmlDocumentMetadata,
    HtmlLink,
    ParsedBlock,
    ParsedDocument,
    ParsedDocxBlock,
    ParsedDocxDocument,
    ParsedHtmlBlock,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextBlock,
    ParsedTextDocument,
    PdfDocumentMetadata,
    PdfPage,
    SourceLocator,
)
from bijux_canon_ingest.domain.semantic_chunking import (
    SemanticChunk,
    SemanticChunkingPolicy,
)
from bijux_canon_ingest.domain.source_admission import (
    AdmissionBudgets,
    AdmissionEvidence,
    AdmissionIssue,
    AdmissionResult,
)
from bijux_canon_ingest.domain.source_discovery import (
    DiscoveredSource,
    DiscoveryLimits,
)
from bijux_canon_ingest.domain.source_mapping import (
    NormalizedSpanMapping,
    SourceByteSpan,
    TextTransformation,
)
from bijux_canon_ingest.domain.source_metadata import (
    CanonicalSourceMetadata,
    MetadataConflict,
    MetadataProvenanceRecord,
    RawMetadataValue,
)

T = TypeVar("T")


class SnapshotReuseError(ValueError):
    """A prior generation cannot safely supply reusable typed members."""


def _typed(value: object, expected: type[T], field: str) -> T:
    if isinstance(value, bool) and expected in {int, float}:
        raise SnapshotReuseError(f"snapshot reuse field {field} is invalid")
    if not isinstance(value, expected):
        raise SnapshotReuseError(f"snapshot reuse field {field} is invalid")
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    return _typed(value, dict, field)


def _sequence(value: object, field: str) -> list[object]:
    return _typed(value, list, field)


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _typed(value, str, field)


def _strings(value: object, field: str) -> tuple[str, ...]:
    return tuple(_typed(item, str, field) for item in _sequence(value, field))


def _pairs(value: object, field: str) -> tuple[tuple[str, str], ...]:
    if isinstance(value, dict):
        return tuple(
            sorted(
                (
                    _typed(key, str, field),
                    _typed(item, str, field),
                )
                for key, item in value.items()
            )
        )
    pairs: list[tuple[str, str]] = []
    for item in _sequence(value, field):
        pair = _sequence(item, field)
        if len(pair) != 2:
            raise SnapshotReuseError(f"snapshot reuse field {field} is invalid")
        pairs.append((_typed(pair[0], str, field), _typed(pair[1], str, field)))
    return tuple(pairs)


def _locator(value: object) -> SourceLocator:
    record = _mapping(value, "locator")
    selectors = _mapping(record.get("selectors"), "locator.selectors")
    return SourceLocator(
        scheme=_typed(record.get("scheme"), str, "locator.scheme"),
        selectors=tuple(
            (
                _typed(name, str, "locator.selector"),
                cast(Any, selector),
            )
            for name, selector in selectors.items()
        ),
    )


def _source(value: object, root_path: Path) -> DiscoveredSource:
    record = _mapping(value, "source")
    relative_path = _typed(record.get("relative_path"), str, "source.relative_path")
    source = DiscoveredSource(
        root_name=_typed(record.get("root_name"), str, "source.root_name"),
        relative_path=relative_path,
        filesystem_path=root_path / relative_path,
        location_id=_typed(record.get("location_id"), str, "source.location_id"),
        content_sha256=_typed(
            record.get("content_sha256"), str, "source.content_sha256"
        ),
        byte_length=_typed(record.get("byte_length"), int, "source.byte_length"),
        media_type=_typed(record.get("media_type"), str, "source.media_type"),
        is_symlink=_typed(record.get("is_symlink"), bool, "source.is_symlink"),
        target_relative_path=_optional_string(
            record.get("target_relative_path"), "source.target_relative_path"
        ),
        duplicate_of_location_id=_optional_string(
            record.get("duplicate_of_location_id"),
            "source.duplicate_of_location_id",
        ),
    )
    if source.identity_payload() != dict(record):
        raise SnapshotReuseError("snapshot reuse source identity does not round-trip")
    return source


def _budgets(value: object) -> AdmissionBudgets:
    record = _mapping(value, "admission.budgets")
    return AdmissionBudgets(**cast(dict[str, Any], dict(record)))


def _admission(value: object, source: DiscoveredSource) -> AdmissionResult:
    record = _mapping(value, "admission")
    evidence = _mapping(record.get("evidence"), "admission.evidence")
    result = AdmissionResult(
        source=source,
        budgets=_budgets(record.get("budgets")),
        disposition=cast(
            Any, _typed(record.get("disposition"), str, "admission.disposition")
        ),
        format_id=cast(
            Any, _optional_string(record.get("format_id"), "admission.format_id")
        ),
        evidence=AdmissionEvidence(**cast(dict[str, Any], dict(evidence))),
        issues=tuple(
            AdmissionIssue(
                code=cast(
                    Any,
                    _typed(
                        _mapping(item, "admission.issue").get("code"),
                        str,
                        "admission.issue.code",
                    ),
                ),
                detail=_typed(
                    _mapping(item, "admission.issue").get("detail"),
                    str,
                    "admission.issue.detail",
                ),
            )
            for item in _sequence(record.get("issues"), "admission.issues")
        ),
    )
    if result.manifest() != dict(record):
        raise SnapshotReuseError(
            "snapshot reuse admission identity does not round-trip"
        )
    return result


def _parser(value: object) -> tuple[str, str]:
    record = _mapping(value, "document.parser")
    return (
        _typed(record.get("name"), str, "document.parser.name"),
        _typed(record.get("version"), str, "document.parser.version"),
    )


def _parsed_document(
    value: object,
    restoration: Mapping[str, object],
) -> SnapshotParsedDocument:
    record = _mapping(value, "document")
    schema = _typed(record.get("schema_version"), str, "document.schema_version")
    parser_name, parser_version = _parser(record.get("parser"))
    source_sha256 = _typed(
        record.get("source_content_sha256"), str, "document.source_content_sha256"
    )
    if schema == "bijux.canon.ingest.parsed_document.v1":
        metadata = _mapping(record.get("metadata"), "document.metadata")
        document: SnapshotParsedDocument = ParsedDocument(
            format_id=_typed(record.get("format_id"), str, "document.format_id"),
            source_content_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            metadata=DocumentMetadata(
                title=_typed(metadata.get("title"), str, "metadata.title"),
                authors=_strings(metadata.get("authors"), "metadata.authors"),
                doi=_typed(metadata.get("doi"), str, "metadata.doi"),
                journal=_typed(metadata.get("journal"), str, "metadata.journal"),
                publication_year=_typed(
                    metadata.get("publication_year"), int, "metadata.publication_year"
                ),
                license_text=_typed(
                    metadata.get("license_text"), str, "metadata.license_text"
                ),
                license_url=_optional_string(
                    metadata.get("license_url"), "metadata.license_url"
                ),
                language=_optional_string(
                    metadata.get("language"), "metadata.language"
                ),
            ),
            blocks=tuple(
                ParsedBlock(
                    index=_typed(block.get("index"), int, "block.index"),
                    role=cast(Any, _typed(block.get("role"), str, "block.role")),
                    text=_typed(block.get("text"), str, "block.text"),
                    source_text=_typed(
                        block.get("source_text"), str, "block.source_text"
                    ),
                    locator=_locator(block.get("locator")),
                    section_path=_strings(
                        block.get("section_path"), "block.section_path"
                    ),
                )
                for block in (
                    _mapping(item, "document.block")
                    for item in _sequence(record.get("blocks"), "document.blocks")
                )
            ),
        )
    elif schema == "bijux.canon.ingest.parsed_pdf_document.v1":
        metadata = _mapping(record.get("metadata"), "document.metadata")
        document = ParsedPdfDocument(
            source_content_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            extractor=_typed(record.get("extractor"), str, "document.extractor"),
            metadata=PdfDocumentMetadata(
                title=_optional_string(metadata.get("title"), "metadata.title"),
                author=_optional_string(metadata.get("author"), "metadata.author"),
                subject=_optional_string(metadata.get("subject"), "metadata.subject"),
                keywords=_optional_string(
                    metadata.get("keywords"), "metadata.keywords"
                ),
                creator=_optional_string(metadata.get("creator"), "metadata.creator"),
                producer=_optional_string(
                    metadata.get("producer"), "metadata.producer"
                ),
                created_at=_optional_string(
                    metadata.get("created_at"), "metadata.created_at"
                ),
                modified_at=_optional_string(
                    metadata.get("modified_at"), "metadata.modified_at"
                ),
                raw_fields=_pairs(metadata.get("raw_fields"), "metadata.raw_fields"),
            ),
            pages=tuple(
                PdfPage(
                    page_number=_typed(page.get("page_number"), int, "page.number"),
                    text=_typed(page.get("text"), str, "page.text"),
                    width_points=_typed(
                        page.get("width_points"), float, "page.width_points"
                    ),
                    height_points=_typed(
                        page.get("height_points"), float, "page.height_points"
                    ),
                    rotation_degrees=_typed(
                        page.get("rotation_degrees"), int, "page.rotation_degrees"
                    ),
                    extraction_method=cast(
                        Any,
                        _typed(
                            page.get("extraction_method"),
                            str,
                            "page.extraction_method",
                        ),
                    ),
                    locator=_locator(page.get("locator")),
                )
                for page in (
                    _mapping(item, "document.page")
                    for item in _sequence(record.get("pages"), "document.pages")
                )
            ),
        )
    elif schema == "bijux.canon.ingest.parsed_html_document.v1":
        metadata = _mapping(record.get("metadata"), "document.metadata")
        document = ParsedHtmlDocument(
            source_content_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            metadata=HtmlDocumentMetadata(
                title=_typed(metadata.get("title"), str, "metadata.title"),
                authors=_strings(metadata.get("authors"), "metadata.authors"),
                doi=_typed(metadata.get("doi"), str, "metadata.doi"),
                language=_optional_string(
                    metadata.get("language"), "metadata.language"
                ),
                canonical_url=_optional_string(
                    metadata.get("canonical_url"), "metadata.canonical_url"
                ),
                raw_meta=_pairs(metadata.get("raw_meta"), "metadata.raw_meta"),
            ),
            blocks=tuple(
                ParsedHtmlBlock(
                    index=_typed(block.get("index"), int, "block.index"),
                    role=cast(Any, _typed(block.get("role"), str, "block.role")),
                    text=_typed(block.get("text"), str, "block.text"),
                    source_text=_typed(
                        block.get("source_text"), str, "block.source_text"
                    ),
                    locator=_locator(block.get("locator")),
                    section_path=_strings(
                        block.get("section_path"), "block.section_path"
                    ),
                    links=tuple(
                        HtmlLink(
                            text=_typed(link.get("text"), str, "link.text"),
                            href=_typed(link.get("href"), str, "link.href"),
                            title=_optional_string(link.get("title"), "link.title"),
                            locator=_locator(link.get("locator")),
                        )
                        for link in (
                            _mapping(item, "block.link")
                            for item in _sequence(block.get("links"), "block.links")
                        )
                    ),
                )
                for block in (
                    _mapping(item, "document.block")
                    for item in _sequence(record.get("blocks"), "document.blocks")
                )
            ),
        )
    elif schema == "bijux.canon.ingest.parsed_text_document.v1":
        normalized_text = _typed(
            restoration.get("normalized_text"), str, "restoration.normalized_text"
        )
        document = ParsedTextDocument(
            format_id=cast(
                Any, _typed(record.get("format_id"), str, "document.format_id")
            ),
            source_content_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            encoding=cast(
                Any, _typed(record.get("encoding"), str, "document.encoding")
            ),
            newline_style=cast(
                Any,
                _typed(record.get("newline_style"), str, "document.newline_style"),
            ),
            normalized_text=normalized_text,
            blocks=tuple(
                ParsedTextBlock(
                    index=_typed(block.get("index"), int, "block.index"),
                    role=cast(Any, _typed(block.get("role"), str, "block.role")),
                    text=_typed(block.get("text"), str, "block.text"),
                    locator=_locator(block.get("locator")),
                    section_path=_strings(
                        block.get("section_path"), "block.section_path"
                    ),
                )
                for block in (
                    _mapping(item, "document.block")
                    for item in _sequence(record.get("blocks"), "document.blocks")
                )
            ),
        )
    elif schema == "bijux.canon.ingest.parsed_docx_document.v1":
        metadata = _mapping(record.get("metadata"), "document.metadata")
        document = ParsedDocxDocument(
            source_content_sha256=source_sha256,
            parser_name=parser_name,
            parser_version=parser_version,
            metadata=DocxDocumentMetadata(
                creator=_optional_string(metadata.get("creator"), "metadata.creator"),
                last_modified_by=_optional_string(
                    metadata.get("last_modified_by"), "metadata.last_modified_by"
                ),
                created_at=_optional_string(
                    metadata.get("created_at"), "metadata.created_at"
                ),
                modified_at=_optional_string(
                    metadata.get("modified_at"), "metadata.modified_at"
                ),
                revision=_optional_string(
                    metadata.get("revision"), "metadata.revision"
                ),
                raw_fields=_pairs(metadata.get("raw_fields"), "metadata.raw_fields"),
            ),
            blocks=tuple(
                ParsedDocxBlock(
                    index=_typed(block.get("index"), int, "block.index"),
                    role=cast(Any, _typed(block.get("role"), str, "block.role")),
                    text=_typed(block.get("text"), str, "block.text"),
                    locator=_locator(block.get("locator")),
                    section_path=_strings(
                        block.get("section_path"), "block.section_path"
                    ),
                    target=_optional_string(block.get("target"), "block.target"),
                )
                for block in (
                    _mapping(item, "document.block")
                    for item in _sequence(record.get("blocks"), "document.blocks")
                )
            ),
        )
    else:
        raise SnapshotReuseError("snapshot reuse parser schema is unsupported")
    if document.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse document does not round-trip")
    return document


def _metadata_value(value: object) -> RawMetadataValue:
    record = _mapping(value, "metadata.value")

    def convert(item: object, field: str) -> Any:
        if isinstance(item, list):
            return tuple(_typed(part, str, field) for part in item)
        return _typed(item, str, field)

    return RawMetadataValue(
        field=cast(Any, _typed(record.get("field"), str, "metadata.value.field")),
        value=convert(record.get("value"), "metadata.value.value"),
        normalized_value=convert(
            record.get("normalized_value"), "metadata.value.normalized_value"
        ),
        source=cast(Any, _typed(record.get("source"), str, "metadata.value.source")),
        provenance=_typed(record.get("provenance"), str, "metadata.value.provenance"),
        provenance_sha256=_typed(
            record.get("provenance_sha256"),
            str,
            "metadata.value.provenance_sha256",
        ),
    )


def _source_metadata(value: object) -> CanonicalSourceMetadata:
    record = _mapping(value, "metadata")
    raw_values = tuple(
        _metadata_value(item)
        for item in _sequence(record.get("raw_values"), "metadata.raw_values")
    )
    selected_values = tuple(
        _metadata_value(item)
        for item in _sequence(record.get("selected_values"), "metadata.selected_values")
    )
    metadata = CanonicalSourceMetadata(
        source_content_sha256=_typed(
            record.get("source_content_sha256"),
            str,
            "metadata.source_content_sha256",
        ),
        format_id=cast(Any, _typed(record.get("format_id"), str, "metadata.format_id")),
        doi=_optional_string(record.get("doi"), "metadata.doi"),
        canonical_uri=_optional_string(
            record.get("canonical_uri"), "metadata.canonical_uri"
        ),
        authors=_strings(record.get("authors"), "metadata.authors"),
        publication_date=_optional_string(
            record.get("publication_date"), "metadata.publication_date"
        ),
        title=_optional_string(record.get("title"), "metadata.title"),
        journal=_optional_string(record.get("journal"), "metadata.journal"),
        language=_optional_string(record.get("language"), "metadata.language"),
        license_expression=_optional_string(
            record.get("license_expression"), "metadata.license_expression"
        ),
        license_url=_optional_string(record.get("license_url"), "metadata.license_url"),
        relative_path=_typed(
            record.get("relative_path"), str, "metadata.relative_path"
        ),
        media_type=_typed(record.get("media_type"), str, "metadata.media_type"),
        provenance_records=tuple(
            MetadataProvenanceRecord(
                source=cast(Any, _typed(item.get("source"), str, "provenance.source")),
                provenance=_typed(item.get("provenance"), str, "provenance.provenance"),
                provenance_sha256=_typed(
                    item.get("provenance_sha256"),
                    str,
                    "provenance.provenance_sha256",
                ),
                format_id=cast(
                    Any,
                    _optional_string(item.get("format_id"), "provenance.format_id"),
                ),
                source_content_sha256=_optional_string(
                    item.get("source_content_sha256"),
                    "provenance.source_content_sha256",
                ),
                source_byte_length=(
                    None
                    if item.get("source_byte_length") is None
                    else _typed(
                        item.get("source_byte_length"),
                        int,
                        "provenance.source_byte_length",
                    )
                ),
                fields=cast(Any, _strings(item.get("fields"), "provenance.fields")),
            )
            for item in (
                _mapping(entry, "metadata.provenance")
                for entry in _sequence(
                    record.get("provenance_records"),
                    "metadata.provenance_records",
                )
            )
        ),
        selected_values=selected_values,
        raw_values=raw_values,
        conflicts=tuple(
            MetadataConflict(
                field=cast(
                    Any, _typed(item.get("field"), str, "metadata.conflict.field")
                ),
                selected=_metadata_value(item.get("selected")),
                alternatives=tuple(
                    _metadata_value(alternative)
                    for alternative in _sequence(
                        item.get("alternatives"), "metadata.conflict.alternatives"
                    )
                ),
            )
            for item in (
                _mapping(entry, "metadata.conflict")
                for entry in _sequence(record.get("conflicts"), "metadata.conflicts")
            )
        ),
    )
    if metadata.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse metadata does not round-trip")
    return metadata


def _span_mapping(value: object) -> NormalizedSpanMapping:
    record = _mapping(value, "mapping")
    source_span = _mapping(record.get("source_span"), "mapping.source_span")
    normalized_span = _mapping(
        record.get("normalized_character_span"), "mapping.normalized_character_span"
    )
    mapping = NormalizedSpanMapping(
        source_content_sha256=_typed(
            record.get("source_content_sha256"),
            str,
            "mapping.source_content_sha256",
        ),
        source_span=SourceByteSpan(
            start=_typed(source_span.get("start"), int, "mapping.source_span.start"),
            end=_typed(source_span.get("end"), int, "mapping.source_span.end"),
            selected_bytes_sha256=_typed(
                source_span.get("selected_bytes_sha256"),
                str,
                "mapping.source_span.selected_bytes_sha256",
            ),
        ),
        locator=_locator(record.get("locator")),
        normalized_text=_typed(
            record.get("normalized_text"), str, "mapping.normalized_text"
        ),
        original_text_sha256=_typed(
            record.get("original_text_sha256"),
            str,
            "mapping.original_text_sha256",
        ),
        normalized_start=_typed(
            normalized_span.get("start"), int, "mapping.normalized_start"
        ),
        normalized_end=_typed(
            normalized_span.get("end"), int, "mapping.normalized_end"
        ),
        transformations=tuple(
            TextTransformation(
                operation=cast(
                    Any,
                    _typed(item.get("operation"), str, "transformation.operation"),
                ),
                implementation=_typed(
                    item.get("implementation"), str, "transformation.implementation"
                ),
                implementation_version=_typed(
                    item.get("implementation_version"),
                    str,
                    "transformation.implementation_version",
                ),
                configuration_sha256=_typed(
                    item.get("configuration_sha256"),
                    str,
                    "transformation.configuration_sha256",
                ),
                input_content_sha256=_typed(
                    item.get("input_content_sha256"),
                    str,
                    "transformation.input_content_sha256",
                ),
                output_content_sha256=_typed(
                    item.get("output_content_sha256"),
                    str,
                    "transformation.output_content_sha256",
                ),
            )
            for item in (
                _mapping(entry, "mapping.transformation")
                for entry in _sequence(
                    record.get("transformations"), "mapping.transformations"
                )
            )
        ),
        parent_mapping_sha256=_optional_string(
            record.get("parent_mapping_sha256"), "mapping.parent_mapping_sha256"
        ),
    )
    if mapping.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse mapping does not round-trip")
    return mapping


def _chunk(
    value: object,
    mappings: Mapping[str, NormalizedSpanMapping],
    block_separator: str,
) -> SemanticChunk:
    record = _mapping(value, "chunk")
    mapping_ids = _strings(record.get("mapping_sha256"), "chunk.mapping_sha256")
    try:
        chunk_mappings = tuple(mappings[identity] for identity in mapping_ids)
    except KeyError as error:
        raise SnapshotReuseError(
            "snapshot reuse chunk mapping is unavailable"
        ) from error
    chunk = SemanticChunk(
        source_content_sha256=_typed(
            record.get("source_content_sha256"), str, "chunk.source_content_sha256"
        ),
        chunk_index=_typed(record.get("chunk_index"), int, "chunk.chunk_index"),
        normalized_text=_typed(
            record.get("normalized_text"), str, "chunk.normalized_text"
        ),
        mappings=chunk_mappings,
        block_roles=_strings(record.get("block_roles"), "chunk.block_roles"),
        section_paths=tuple(
            _strings(path, "chunk.section_path")
            for path in _sequence(record.get("section_paths"), "chunk.section_paths")
        ),
        overlap_character_count=_typed(
            record.get("overlap_character_count"),
            int,
            "chunk.overlap_character_count",
        ),
        chunking_policy_sha256=_typed(
            record.get("chunking_policy_sha256"),
            str,
            "chunk.chunking_policy_sha256",
        ),
        block_separator=block_separator,
    )
    if chunk.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse chunk does not round-trip")
    return chunk


def _configuration(value: object) -> CorpusSnapshotConfiguration:
    record = _mapping(value, "configuration")
    discovery = _mapping(record.get("discovery_limits"), "configuration.discovery")
    budgets = _mapping(record.get("admission_budgets"), "configuration.admission")
    chunking = _mapping(record.get("chunking_policy"), "configuration.chunking")
    chunking_schema = _typed(
        chunking.get("schema_version"), str, "chunking.schema_version"
    )
    if chunking_schema not in {
        "bijux.canon.ingest.semantic_chunking_policy.v1",
        "bijux.canon.ingest.semantic_chunking_policy.v2",
    }:
        raise SnapshotReuseError("configuration chunking schema is unsupported")
    boundary_strategy = (
        "hard"
        if chunking_schema == "bijux.canon.ingest.semantic_chunking_policy.v1"
        else _typed(
            chunking.get("boundary_strategy"), str, "chunking.boundary_strategy"
        )
    )
    if boundary_strategy not in {"hard", "sentence"}:
        raise SnapshotReuseError("configuration chunking strategy is unsupported")
    configuration = CorpusSnapshotConfiguration(
        corpus_name=_typed(record.get("corpus_name"), str, "configuration.corpus_name"),
        discovery_limits=DiscoveryLimits(**cast(dict[str, Any], dict(discovery))),
        admission_budgets=AdmissionBudgets(**cast(dict[str, Any], dict(budgets))),
        chunking_policy=SemanticChunkingPolicy(
            max_characters=_typed(
                chunking.get("max_characters"), int, "chunking.max_characters"
            ),
            overlap_characters=_typed(
                chunking.get("overlap_characters"),
                int,
                "chunking.overlap_characters",
            ),
            block_separator=_typed(
                chunking.get("block_separator"), str, "chunking.block_separator"
            ),
            boundary_strategy=cast(Literal["hard", "sentence"], boundary_strategy),
        ),
    )
    if configuration.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse configuration does not round-trip")
    return configuration


def _snapshot_document(
    bundle: Mapping[str, object],
    root_path: Path,
    block_separator: str,
) -> CorpusSnapshotDocument:
    record = _mapping(bundle.get("snapshot_document"), "snapshot_document")
    source = _source(bundle.get("source"), root_path)
    restoration = _mapping(bundle.get("restoration", {}), "restoration")
    mappings = tuple(
        _span_mapping(item)
        for item in _sequence(record.get("mappings"), "snapshot_document.mappings")
    )
    mapping_by_id = {mapping.mapping_sha256: mapping for mapping in mappings}
    for raw_mapping in _sequence(
        bundle.get("chunk_mappings"), "snapshot_document.chunk_mappings"
    ):
        chunk_mapping = _span_mapping(raw_mapping)
        existing = mapping_by_id.setdefault(chunk_mapping.mapping_sha256, chunk_mapping)
        if existing != chunk_mapping:
            raise SnapshotReuseError("snapshot reuse mapping identity is ambiguous")
    document = CorpusSnapshotDocument(
        admission=_admission(record.get("admission"), source),
        document=_parsed_document(record.get("document"), restoration),
        metadata=_source_metadata(record.get("metadata")),
        mappings=mappings,
        chunks=tuple(
            _chunk(item, mapping_by_id, block_separator)
            for item in _sequence(record.get("chunks"), "snapshot_document.chunks")
        ),
    )
    if document.manifest() != dict(record):
        raise SnapshotReuseError("snapshot reuse document graph does not round-trip")
    return document


def restore_published_corpus_snapshot(
    publication: PublishedCorpusSnapshot,
    bundles: tuple[dict[str, object], ...],
    *,
    root_path: Path,
) -> CorpusSnapshot:
    """Restore one verified publication or refuse incomplete reuse evidence."""

    try:
        manifest = json.loads(publication.canonical_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotReuseError("published snapshot JSON is invalid") from error
    if not isinstance(manifest, dict):
        raise SnapshotReuseError("published snapshot manifest is invalid")
    configuration = _configuration(manifest.get("configuration"))
    documents_by_id: dict[str, Mapping[str, object]] = {}
    rejection_bundles: list[Mapping[str, object]] = []
    for raw_bundle in bundles:
        bundle = _mapping(raw_bundle, "bundle")
        kind = bundle.get("kind")
        if kind == "document":
            record = _mapping(bundle.get("snapshot_document"), "snapshot_document")
            document_id = _typed(
                record.get("document_id"), str, "snapshot_document.document_id"
            )
            if document_id in documents_by_id:
                raise SnapshotReuseError("duplicate snapshot reuse document")
            documents_by_id[document_id] = bundle
        elif kind == "rejection":
            rejection_bundles.append(bundle)
        else:
            raise SnapshotReuseError("snapshot reuse bundle kind is unsupported")
    expected_documents = _sequence(manifest.get("documents"), "snapshot.documents")
    documents: list[CorpusSnapshotDocument] = []
    for raw_document in expected_documents:
        document_record = _mapping(raw_document, "snapshot.document")
        document_id = _typed(
            document_record.get("document_id"), str, "snapshot.document_id"
        )
        document_bundle = documents_by_id.get(document_id)
        if document_bundle is None:
            raise SnapshotReuseError("snapshot reuse document is unavailable")
        documents.append(
            _snapshot_document(
                document_bundle,
                root_path,
                configuration.chunking_policy.block_separator,
            )
        )
    if len(documents_by_id) != len(expected_documents):
        raise SnapshotReuseError("snapshot reuse document coverage is invalid")
    rejection_by_manifest = {
        json.dumps(
            bundle.get("rejection"), sort_keys=True, separators=(",", ":")
        ): bundle
        for bundle in rejection_bundles
    }
    rejections: list[AdmissionResult] = []
    for raw_rejection in _sequence(manifest.get("rejections"), "snapshot.rejections"):
        key = json.dumps(raw_rejection, sort_keys=True, separators=(",", ":"))
        rejection_bundle = rejection_by_manifest.get(key)
        if rejection_bundle is None:
            raise SnapshotReuseError("snapshot reuse rejection is unavailable")
        rejections.append(
            _admission(
                rejection_bundle.get("rejection"),
                _source(rejection_bundle.get("source"), root_path),
            )
        )
    if len(rejection_bundles) != len(rejections):
        raise SnapshotReuseError("snapshot reuse rejection coverage is invalid")
    snapshot = CorpusSnapshot(configuration, tuple(documents), tuple(rejections))
    if (
        snapshot.snapshot_id != publication.snapshot_id
        or snapshot.canonical_bytes != publication.canonical_bytes
    ):
        raise SnapshotReuseError("restored snapshot identity does not round-trip")
    return snapshot


__all__ = ["SnapshotReuseError", "restore_published_corpus_snapshot"]
