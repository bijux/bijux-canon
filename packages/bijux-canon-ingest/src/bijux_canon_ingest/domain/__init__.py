# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Pure, production-facing architecture primitives.

This package adds a domain layer around the pure ingestion core:
- Capability protocols (typed `Protocol`s)
- Structured logs as pure data (`LogEntry` + Writer)
- Idempotent effect design for safe retries/replays

Note: `IOPlan` + IOPlan-specific retry/tx helpers live in `bijux_canon_ingest.domain.effects`.
"""

from __future__ import annotations

from .capabilities import Cache, Clock, Logger, Storage, StorageRead, StorageWrite
from .composition import chain_io, logged_read
from .corpus_delta import (
    CorpusDelta,
    SourceModification,
    SourceRename,
    SourceTombstone,
    TombstoneReason,
)
from .corpus_publication import (
    PublishedCorpusSnapshot,
    RecoveryStatus,
    SnapshotRecovery,
)
from .corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    SnapshotParsedDocument,
)
from .document_extraction import (
    BlockRole,
    DocumentMetadata,
    DocumentParseError,
    DocumentParseIssueCode,
    DocxBlockRole,
    DocxDocumentMetadata,
    HtmlBlockRole,
    HtmlDocumentMetadata,
    HtmlLink,
    NewlineStyle,
    OcrRequiredOutcome,
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
    PdfPageExtraction,
    SourceLocator,
    TextBlockRole,
    TextEncoding,
)
from .idempotent import AtomicWriteCap, content_key, idempotent_write
from .logging import LogEntry, LogMonoid, Logs, log_tell, trace_stage, trace_value
from .semantic_chunking import SemanticChunk, SemanticChunkingPolicy
from .source_discovery import (
    DiscoveredSource,
    DiscoveryIssue,
    DiscoveryIssueCode,
    DiscoveryLimits,
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
    SymlinkPolicy,
)
from .source_mapping import (
    NormalizedSpanMapping,
    SourceByteSpan,
    TextTransformation,
    TransformationOperation,
)
from .source_metadata import (
    METADATA_SOURCE_PRECEDENCE,
    CanonicalSourceMetadata,
    MetadataConflict,
    MetadataField,
    MetadataProvenanceRecord,
    MetadataSource,
    MetadataValue,
    RawMetadataValue,
)

__all__ = [
    # Logging (pure data)
    "LogEntry",
    "Logs",
    "LogMonoid",
    "log_tell",
    "trace_stage",
    "trace_value",
    # Capabilities
    "StorageRead",
    "StorageWrite",
    "Storage",
    "Clock",
    "Logger",
    "Cache",
    # Composition helpers
    "chain_io",
    "logged_read",
    # Idempotency + retry
    "AtomicWriteCap",
    "content_key",
    "idempotent_write",
    # Source discovery
    "DiscoveredSource",
    "DiscoveryIssue",
    "DiscoveryIssueCode",
    "DiscoveryLimits",
    "DiscoveryPolicy",
    "DiscoveryResult",
    "DiscoveryRoot",
    "SymlinkPolicy",
    # Source metadata
    "METADATA_SOURCE_PRECEDENCE",
    "CanonicalSourceMetadata",
    "MetadataConflict",
    "MetadataField",
    "MetadataProvenanceRecord",
    "MetadataSource",
    "MetadataValue",
    "RawMetadataValue",
    # Corpus snapshots
    "CorpusSnapshot",
    "CorpusSnapshotConfiguration",
    "CorpusSnapshotDocument",
    "SnapshotParsedDocument",
    # Corpus deltas
    "CorpusDelta",
    "SourceModification",
    "SourceRename",
    "SourceTombstone",
    "TombstoneReason",
    # Corpus publication
    "PublishedCorpusSnapshot",
    "RecoveryStatus",
    "SnapshotRecovery",
    # Semantic chunks
    "SemanticChunk",
    "SemanticChunkingPolicy",
    # Source mappings
    "NormalizedSpanMapping",
    "SourceByteSpan",
    "TextTransformation",
    "TransformationOperation",
    # Document extraction
    "BlockRole",
    "DocumentMetadata",
    "DocumentParseError",
    "DocumentParseIssueCode",
    "DocxBlockRole",
    "DocxDocumentMetadata",
    "HtmlBlockRole",
    "HtmlDocumentMetadata",
    "HtmlLink",
    "NewlineStyle",
    "OcrRequiredOutcome",
    "ParsedBlock",
    "ParsedDocument",
    "ParsedDocxBlock",
    "ParsedDocxDocument",
    "ParsedHtmlBlock",
    "ParsedHtmlDocument",
    "ParsedPdfDocument",
    "ParsedTextBlock",
    "ParsedTextDocument",
    "PdfDocumentMetadata",
    "PdfPage",
    "PdfPageExtraction",
    "SourceLocator",
    "TextBlockRole",
    "TextEncoding",
]
