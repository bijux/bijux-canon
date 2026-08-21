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
from .document_extraction import (
    BlockRole,
    DocumentMetadata,
    DocumentParseError,
    DocumentParseIssueCode,
    HtmlBlockRole,
    HtmlDocumentMetadata,
    HtmlLink,
    ParsedBlock,
    ParsedDocument,
    ParsedHtmlBlock,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    PdfDocumentMetadata,
    PdfPage,
    PdfPageExtraction,
    SourceLocator,
)
from .idempotent import AtomicWriteCap, content_key, idempotent_write
from .logging import LogEntry, LogMonoid, Logs, log_tell, trace_stage, trace_value
from .source_discovery import (
    DiscoveredSource,
    DiscoveryIssue,
    DiscoveryIssueCode,
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
    SymlinkPolicy,
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
    "DiscoveryPolicy",
    "DiscoveryResult",
    "DiscoveryRoot",
    "SymlinkPolicy",
    # Document extraction
    "BlockRole",
    "DocumentMetadata",
    "DocumentParseError",
    "DocumentParseIssueCode",
    "HtmlBlockRole",
    "HtmlDocumentMetadata",
    "HtmlLink",
    "ParsedBlock",
    "ParsedDocument",
    "ParsedHtmlBlock",
    "ParsedHtmlDocument",
    "ParsedPdfDocument",
    "PdfDocumentMetadata",
    "PdfPage",
    "PdfPageExtraction",
    "SourceLocator",
]
