# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical directory-to-snapshot ingestion service shared by every boundary."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from bijux_canon_ingest.application.corpus_publication import publish_corpus_snapshot
from bijux_canon_ingest.application.corpus_snapshot import build_corpus_snapshot
from bijux_canon_ingest.application.document_extraction import (
    assess_ocr_requirement,
    parse_docx,
    parse_html,
    parse_jats,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from bijux_canon_ingest.application.semantic_chunking import chunk_document_mappings
from bijux_canon_ingest.application.source_admission import admit_sources
from bijux_canon_ingest.application.source_discovery import discover_sources
from bijux_canon_ingest.application.source_mapping import (
    ParsedSourceDocument,
    build_document_span_mappings,
)
from bijux_canon_ingest.application.source_metadata import normalize_source_metadata
from bijux_canon_ingest.domain.corpus_publication import PublishedCorpusSnapshot
from bijux_canon_ingest.domain.corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
)
from bijux_canon_ingest.domain.document_extraction import OcrRequiredOutcome
from bijux_canon_ingest.domain.source_admission import AdmissionResult
from bijux_canon_ingest.domain.source_discovery import (
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
    SymlinkPolicy,
)
from bijux_canon_ingest.infra.adapters.file_admission import read_current_source


class CanonicalIngestError(RuntimeError):
    """A canonical corpus could not be assembled from the requested root."""


@dataclass(frozen=True, slots=True)
class CanonicalIngestRequest:
    """Portable configuration accepted identically by installed boundaries."""

    root_path: Path
    root_name: str
    configuration: CorpusSnapshotConfiguration
    include: tuple[str, ...] = ("**/*",)
    exclude: tuple[str, ...] = ()
    symlink_policy: SymlinkPolicy = "reject"
    publication_root: Path | None = None


@dataclass(frozen=True, slots=True)
class CanonicalIngestResult:
    """Canonical snapshot plus the stable summary exposed at every boundary."""

    snapshot: CorpusSnapshot
    discovery: DiscoveryResult
    ocr_required: tuple[OcrRequiredOutcome, ...]
    publication: PublishedCorpusSnapshot | None

    def manifest(self) -> dict[str, object]:
        formats: dict[str, int] = {}
        for document in self.snapshot.documents:
            format_id = document.admission.format_id
            assert format_id is not None
            formats[format_id] = formats.get(format_id, 0) + 1
        canonical_bytes = self.snapshot.canonical_bytes
        return {
            "canonical_byte_length": len(canonical_bytes),
            "canonical_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
            "chunk_count": sum(
                len(document.chunks) for document in self.snapshot.documents
            ),
            "configuration_sha256": self.snapshot.configuration.configuration_sha256,
            "discovery_issue_count": len(self.discovery.issues),
            "document_count": len(self.snapshot.documents),
            "formats": dict(sorted(formats.items())),
            "ocr_required_count": len(self.ocr_required),
            "publication": (
                self.publication.manifest() if self.publication is not None else None
            ),
            "rejection_count": len(self.snapshot.rejections),
            "schema_version": "bijux.canon.ingest.result.v1",
            "snapshot_id": self.snapshot.snapshot_id,
        }


def _parse(admission: AdmissionResult) -> ParsedSourceDocument:
    if admission.format_id == "docx":
        return parse_docx(admission)
    if admission.format_id == "html":
        return parse_html(admission)
    if admission.format_id == "jats":
        return parse_jats(admission)
    if admission.format_id == "markdown":
        return parse_markdown(admission)
    if admission.format_id == "pdf-digital":
        return parse_pdf(admission)
    if admission.format_id == "text":
        return parse_text(admission)
    raise CanonicalIngestError(
        f"no canonical parser for format {admission.format_id!r}"
    )


class CanonicalIngestRuntime:
    """Runtime adapter around the canonical application service."""

    def ingest(self, request: CanonicalIngestRequest) -> CanonicalIngestResult:
        discovery = discover_sources(
            DiscoveryPolicy(
                roots=(DiscoveryRoot(request.root_name, request.root_path),),
                include=request.include,
                exclude=request.exclude,
                symlink_policy=request.symlink_policy,
            )
        )
        if not discovery.complete:
            codes = ", ".join(sorted({issue.code for issue in discovery.issues}))
            raise CanonicalIngestError(f"source discovery is incomplete: {codes}")
        admissions = admit_sources(
            discovery.sources,
            budgets=request.configuration.admission_budgets,
        )
        documents: list[CorpusSnapshotDocument] = []
        rejections: list[AdmissionResult] = []
        ocr_required: list[OcrRequiredOutcome] = []
        for admission in admissions:
            if not admission.admitted:
                rejections.append(admission)
                continue
            if admission.format_id == "ocr-required":
                ocr_required.append(assess_ocr_requirement(admission))
                continue
            if admission.format_id is None:
                raise CanonicalIngestError("admitted source has no format identity")
            parsed = _parse(admission)
            content = read_current_source(admission.source, admission.budgets)
            metadata = normalize_source_metadata(
                admission.source,
                format_id=admission.format_id,
            )
            mappings = build_document_span_mappings(content, parsed)
            chunks = chunk_document_mappings(
                parsed,
                mappings,
                policy=request.configuration.chunking_policy,
            )
            documents.append(
                CorpusSnapshotDocument(
                    admission,
                    parsed,
                    metadata,
                    mappings,
                    chunks,
                )
            )
        if not documents:
            raise CanonicalIngestError("no supported documents were admitted")
        snapshot = build_corpus_snapshot(
            request.configuration,
            documents,
            rejections=rejections,
        )
        publication = (
            publish_corpus_snapshot(request.publication_root, snapshot)
            if request.publication_root is not None
            else None
        )
        return CanonicalIngestResult(
            snapshot,
            discovery,
            tuple(ocr_required),
            publication,
        )


def ingest_corpus(request: CanonicalIngestRequest) -> CanonicalIngestResult:
    """Run canonical ingestion through the default installed runtime adapter."""

    return CanonicalIngestRuntime().ingest(request)


__all__ = [
    "CanonicalIngestError",
    "CanonicalIngestRequest",
    "CanonicalIngestResult",
    "CanonicalIngestRuntime",
    "ingest_corpus",
]
