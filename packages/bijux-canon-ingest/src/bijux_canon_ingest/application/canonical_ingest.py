# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical directory-to-snapshot ingestion service shared by every boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bijux_canon_ingest.application.corpus_delta import plan_corpus_delta
from bijux_canon_ingest.application.corpus_lock import (
    VerifiedCorpusLock,
    load_verified_corpus_lock,
)
from bijux_canon_ingest.application.corpus_publication import (
    publish_corpus_snapshot,
    read_published_corpus_snapshot,
    read_published_snapshot_reuse_bundles,
)
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
from bijux_canon_ingest.application.parsed_metadata import (
    metadata_record_from_parsed_document,
)
from bijux_canon_ingest.application.semantic_chunking import chunk_document_mappings
from bijux_canon_ingest.application.snapshot_reuse import (
    SnapshotReuseError,
    restore_published_corpus_snapshot,
)
from bijux_canon_ingest.application.source_admission import admit_sources
from bijux_canon_ingest.application.source_discovery import discover_sources
from bijux_canon_ingest.application.source_mapping import (
    ParsedSourceDocument,
    build_document_span_mappings,
)
from bijux_canon_ingest.application.source_metadata import normalize_source_metadata
from bijux_canon_ingest.domain.corpus_delta import CorpusDelta
from bijux_canon_ingest.domain.corpus_publication import PublishedCorpusSnapshot
from bijux_canon_ingest.domain.corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
)
from bijux_canon_ingest.domain.document_extraction import OcrRequiredOutcome
from bijux_canon_ingest.domain.source_admission import AdmissionResult
from bijux_canon_ingest.domain.source_discovery import (
    DiscoveryLimits,
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
    SymlinkPolicy,
)
from bijux_canon_ingest.infra.adapters.file_admission import read_current_source
from bijux_canon_ingest.infra.parsers.docx import parser_identity as docx_identity
from bijux_canon_ingest.infra.parsers.html import parser_identity as html_identity
from bijux_canon_ingest.infra.parsers.jats import parser_identity as jats_identity
from bijux_canon_ingest.infra.parsers.pdf import parser_identity as pdf_identity
from bijux_canon_ingest.infra.parsers.text import parser_identity as text_identity


class CanonicalIngestError(RuntimeError):
    """A canonical corpus could not be assembled from the requested root."""


_DEFAULT_DISCOVERY_LIMITS = DiscoveryLimits()
IngestDisposition = Literal["initial", "unchanged", "changed"]


@dataclass(frozen=True, slots=True)
class CorpusDiscoveryLimits:
    """Transport-neutral source bounds translated at the application boundary."""

    max_depth: int = _DEFAULT_DISCOVERY_LIMITS.max_depth
    max_entries: int = _DEFAULT_DISCOVERY_LIMITS.max_entries
    max_files: int = _DEFAULT_DISCOVERY_LIMITS.max_files
    max_file_bytes: int = _DEFAULT_DISCOVERY_LIMITS.max_file_bytes
    max_total_bytes: int = _DEFAULT_DISCOVERY_LIMITS.max_total_bytes
    max_seconds: float = _DEFAULT_DISCOVERY_LIMITS.max_seconds

    def to_domain(self) -> DiscoveryLimits:
        """Validate and return the domain-owned discovery limit value."""
        return DiscoveryLimits(
            max_depth=self.max_depth,
            max_entries=self.max_entries,
            max_files=self.max_files,
            max_file_bytes=self.max_file_bytes,
            max_total_bytes=self.max_total_bytes,
            max_seconds=self.max_seconds,
        )


@dataclass(frozen=True, slots=True)
class CanonicalIngestRequest:
    """Portable configuration accepted identically by installed boundaries."""

    root_path: Path
    root_name: str
    configuration: CorpusSnapshotConfiguration
    include: tuple[str, ...] = ("**/*",)
    exclude: tuple[str, ...] = ()
    symlink_policy: SymlinkPolicy = "reject"
    corpus_lock_path: Path | None = None
    publication_root: Path | None = None

    @classmethod
    def for_directory(
        cls,
        *,
        root_path: Path,
        root_name: str,
        corpus_name: str,
        discovery_limits: CorpusDiscoveryLimits | None = None,
        include: tuple[str, ...] = ("**/*",),
        exclude: tuple[str, ...] = (),
        symlink_policy: SymlinkPolicy = "reject",
        corpus_lock_path: Path | None = None,
        publication_root: Path | None = None,
    ) -> CanonicalIngestRequest:
        """Translate portable directory inputs into the domain configuration."""
        return cls(
            root_path=root_path,
            root_name=root_name,
            configuration=CorpusSnapshotConfiguration(
                corpus_name=corpus_name,
                discovery_limits=(
                    CorpusDiscoveryLimits()
                    if discovery_limits is None
                    else discovery_limits
                ).to_domain(),
            ),
            include=include,
            exclude=exclude,
            symlink_policy=symlink_policy,
            corpus_lock_path=corpus_lock_path,
            publication_root=publication_root,
        )


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


def _corpus_lock_manifest(lock: VerifiedCorpusLock | None) -> dict[str, object]:
    return lock.manifest() if lock is not None else {"status": "absent"}


@dataclass(frozen=True, slots=True)
class CanonicalCorpusPreparation:
    """Validated source documents before immutable snapshot assembly."""

    configuration: CorpusSnapshotConfiguration
    documents: tuple[CorpusSnapshotDocument, ...]
    rejections: tuple[AdmissionResult, ...]
    discovery: DiscoveryResult
    ocr_required: tuple[OcrRequiredOutcome, ...]
    corpus_lock: VerifiedCorpusLock | None

    def __post_init__(self) -> None:
        if not self.documents:
            raise ValueError("corpus preparation requires admitted documents")
        if not self.discovery.complete:
            raise ValueError("corpus preparation requires complete discovery")
        if self.corpus_lock is not None and len(self.corpus_lock.sources) != len(
            self.discovery.sources
        ):
            raise ValueError("corpus preparation lock coverage is incomplete")

    def snapshot(self) -> CorpusSnapshot:
        """Assemble the distinct immutable snapshot operation in memory."""
        return build_corpus_snapshot(
            self.configuration,
            self.documents,
            rejections=self.rejections,
        )

    def retained_sources(self) -> tuple[CanonicalRetainedSource, ...]:
        """Re-read and verify admitted source bytes for durable CAS retention."""
        retained = []
        for document in sorted(
            self.documents,
            key=lambda item: item.admission.source.relative_path,
        ):
            source = document.admission.source
            content = read_current_source(source, document.admission.budgets)
            retained.append(
                CanonicalRetainedSource(
                    relative_path=source.relative_path,
                    media_type=source.media_type,
                    content_sha256=source.content_sha256,
                    content=content,
                )
            )
        return tuple(retained)

    def manifest(self) -> dict[str, object]:
        """Return restart-safe source-document input for snapshot assembly."""
        payload: dict[str, object] = {
            "configuration": self.configuration.manifest(),
            "configuration_sha256": self.configuration.configuration_sha256,
            "corpus_lock": _corpus_lock_manifest(self.corpus_lock),
            "discovery": self.discovery.manifest(),
            "documents": [document.manifest() for document in self.documents],
            "ocr_required": [outcome.manifest() for outcome in self.ocr_required],
            "rejections": [rejection.manifest() for rejection in self.rejections],
            "schema_version": "bijux.canon.ingest.corpus_preparation.v2",
        }
        return {"preparation_id": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class CanonicalRetainedSource:
    """One verified original source payload prepared for immutable retention."""

    relative_path: str
    media_type: str
    content_sha256: str
    content: bytes

    def __post_init__(self) -> None:
        if not self.relative_path or self.relative_path.startswith("/"):
            raise ValueError("retained source path must be portable and relative")
        if hashlib.sha256(self.content).hexdigest() != self.content_sha256:
            raise ValueError("retained source bytes do not match their identity")
        if "/" not in self.media_type:
            raise ValueError("retained source media type is invalid")


def assemble_corpus_snapshot_manifest(
    preparation: Mapping[str, object],
) -> dict[str, object]:
    """Assemble and validate a snapshot manifest from persisted preparation."""
    record = dict(preparation)
    schema_version = record.get("schema_version")
    if schema_version not in {
        "bijux.canon.ingest.corpus_preparation.v1",
        "bijux.canon.ingest.corpus_preparation.v2",
    }:
        raise ValueError("corpus preparation schema is unsupported")
    preparation_id = record.pop("preparation_id", None)
    if preparation_id != _identity(record):
        raise ValueError("corpus preparation identity is invalid")
    configuration = record.get("configuration")
    documents = record.get("documents")
    rejections = record.get("rejections")
    discovery = record.get("discovery")
    corpus_lock = record.get("corpus_lock", {"status": "absent"})
    if not isinstance(configuration, dict):
        raise ValueError("corpus preparation configuration is invalid")
    if not isinstance(documents, list) or not documents:
        raise ValueError("corpus preparation documents are invalid")
    if not isinstance(rejections, list):
        raise ValueError("corpus preparation rejections are invalid")
    if not isinstance(discovery, dict) or discovery.get("complete") is not True:
        raise ValueError("corpus preparation discovery is incomplete")
    if not isinstance(corpus_lock, dict) or corpus_lock.get("status") not in {
        "absent",
        "verified",
    }:
        raise ValueError("corpus preparation lock evidence is invalid")
    if corpus_lock["status"] == "verified" and (
        corpus_lock.get("schema_version")
        not in {
            "bijux.canon.parser_source_lock.v1",
            "bijux.canon.research_corpus_lock.v1",
        }
        or corpus_lock.get("discovery") not in {"automatic", "explicit"}
        or not isinstance(corpus_lock.get("source_count"), int)
        or isinstance(corpus_lock.get("source_count"), bool)
        or corpus_lock["source_count"] <= 0
        or not isinstance(corpus_lock.get("lock_identity_sha256"), str)
        or len(corpus_lock["lock_identity_sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in corpus_lock["lock_identity_sha256"]
        )
    ):
        raise ValueError("corpus preparation verified lock evidence is invalid")
    if record.get("configuration_sha256") != _identity(configuration):
        raise ValueError("corpus preparation configuration identity is invalid")
    if any(not isinstance(item, dict) for item in documents + rejections):
        raise ValueError("corpus preparation membership is invalid")
    payload: dict[str, object] = {
        "configuration": configuration,
        "configuration_sha256": record["configuration_sha256"],
        "documents": documents,
        "rejections": rejections,
        "schema_version": "bijux.canon.ingest.corpus_snapshot.v1",
    }
    return {"snapshot_id": _identity(payload), **payload}


@dataclass(frozen=True, slots=True)
class CanonicalIngestResult:
    """Canonical snapshot plus the stable summary exposed at every boundary."""

    snapshot: CorpusSnapshot
    discovery: DiscoveryResult
    ocr_required: tuple[OcrRequiredOutcome, ...]
    publication: PublishedCorpusSnapshot | None
    corpus_lock: VerifiedCorpusLock | None
    disposition: IngestDisposition = "initial"
    delta: CorpusDelta | None = None

    def __post_init__(self) -> None:
        if self.disposition == "initial":
            if self.delta is not None:
                raise ValueError("initial ingest result cannot declare a delta")
            return
        if (
            self.delta is None
            or self.delta.current_snapshot_id != self.snapshot.snapshot_id
        ):
            raise ValueError("incremental ingest result requires its exact delta")
        if self.delta.is_noop != (self.disposition == "unchanged"):
            raise ValueError(
                "ingest disposition does not match its snapshot transition"
            )

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
            "corpus_lock": _corpus_lock_manifest(self.corpus_lock),
            "discovery_issue_count": len(self.discovery.issues),
            "disposition": self.disposition,
            "document_count": len(self.snapshot.documents),
            "delta": self.delta.manifest() if self.delta is not None else None,
            "formats": dict(sorted(formats.items())),
            "ocr_required_count": len(self.ocr_required),
            "publication": (
                self.publication.manifest() if self.publication is not None else None
            ),
            "rejection_count": len(self.snapshot.rejections),
            "schema_version": "bijux.canon.ingest.result.v2",
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


def _parser_identity(format_id: str) -> tuple[str, str, str]:
    if format_id == "docx":
        return docx_identity()
    if format_id == "html":
        return html_identity()
    if format_id == "jats":
        return jats_identity()
    if format_id in {"markdown", "text"}:
        return text_identity(format_id)
    if format_id == "pdf-digital":
        return pdf_identity()
    raise CanonicalIngestError(f"no canonical parser identity for format {format_id!r}")


def _document_parser_identity(
    document: ParsedSourceDocument,
) -> tuple[str, str, str]:
    manifest = document.manifest()
    parser = manifest.get("parser")
    schema_version = manifest.get("schema_version")
    if not isinstance(parser, dict) or not isinstance(schema_version, str):
        raise CanonicalIngestError("persisted parser identity is invalid")
    name = parser.get("name")
    version = parser.get("version")
    if not isinstance(name, str) or not isinstance(version, str):
        raise CanonicalIngestError("persisted parser identity is invalid")
    return name, version, schema_version


class CanonicalIngestRuntime:
    """Runtime adapter around the canonical application service."""

    @staticmethod
    def _previous_snapshot(
        request: CanonicalIngestRequest,
    ) -> CorpusSnapshot | None:
        if request.publication_root is None:
            return None
        publication = read_published_corpus_snapshot(request.publication_root)
        if publication is None:
            return None
        bundles = read_published_snapshot_reuse_bundles(request.publication_root)
        if not bundles:
            return None
        try:
            return restore_published_corpus_snapshot(
                publication,
                bundles,
                root_path=request.root_path,
            )
        except SnapshotReuseError as error:
            raise CanonicalIngestError(
                "published snapshot reuse integrity failed"
            ) from error

    def prepare(
        self,
        request: CanonicalIngestRequest,
        *,
        previous_snapshot: CorpusSnapshot | None = None,
    ) -> CanonicalCorpusPreparation:
        """Discover, admit, extract, and chunk without assembling a snapshot."""
        exclude = list(request.exclude)
        if "corpus.lock.json" not in exclude:
            exclude.append("corpus.lock.json")
        if request.corpus_lock_path is not None:
            try:
                lock_relative = request.corpus_lock_path.resolve().relative_to(
                    request.root_path.resolve()
                )
            except ValueError:
                pass
            else:
                lock_pattern = lock_relative.as_posix()
                if lock_pattern not in exclude:
                    exclude.append(lock_pattern)
        discovery = discover_sources(
            DiscoveryPolicy(
                roots=(DiscoveryRoot(request.root_name, request.root_path),),
                include=request.include,
                exclude=tuple(exclude),
                symlink_policy=request.symlink_policy,
                limits=request.configuration.discovery_limits,
            )
        )
        if not discovery.complete:
            codes = ", ".join(sorted({issue.code for issue in discovery.issues}))
            raise CanonicalIngestError(f"source discovery is incomplete: {codes}")
        corpus_lock = load_verified_corpus_lock(
            request.root_path,
            discovery.sources,
            lock_path=request.corpus_lock_path,
        )
        admissions = admit_sources(
            discovery.sources,
            budgets=request.configuration.admission_budgets,
        )
        documents: list[CorpusSnapshotDocument] = []
        rejections: list[AdmissionResult] = []
        ocr_required: list[OcrRequiredOutcome] = []
        previous_by_location = {
            document.admission.source.location_id: document
            for document in (
                previous_snapshot.documents if previous_snapshot is not None else ()
            )
        }
        previous_by_content: dict[tuple[str, str], list[CorpusSnapshotDocument]] = {}
        for document in previous_by_location.values():
            format_id = document.admission.format_id
            if format_id is None:
                continue
            previous_by_content.setdefault(
                (document.admission.source.content_sha256, format_id), []
            ).append(document)
        for candidates in previous_by_content.values():
            candidates.sort(key=lambda item: item.admission.source.location_id)
        for admission in admissions:
            if not admission.admitted:
                rejections.append(admission)
                continue
            if admission.format_id == "ocr-required":
                ocr_required.append(assess_ocr_requirement(admission))
                continue
            if admission.format_id is None:
                raise CanonicalIngestError("admitted source has no format identity")
            previous_document = previous_by_location.get(admission.source.location_id)
            if (
                previous_document is None
                or previous_document.admission.source.content_sha256
                != admission.source.content_sha256
                or previous_document.admission.format_id != admission.format_id
            ):
                candidates = previous_by_content.get(
                    (admission.source.content_sha256, admission.format_id), []
                )
                previous_document = candidates[0] if candidates else None
            parser_reused = previous_document is not None and _document_parser_identity(
                previous_document.document
            ) == _parser_identity(admission.format_id)
            parsed = (
                previous_document.document
                if parser_reused and previous_document is not None
                else _parse(admission)
            )
            content = read_current_source(admission.source, admission.budgets)
            metadata = normalize_source_metadata(
                admission.source,
                format_id=admission.format_id,
                records=(
                    *(
                        corpus_lock.records_for(admission.source)
                        if corpus_lock is not None
                        else ()
                    ),
                    metadata_record_from_parsed_document(
                        parsed,
                        source_byte_length=admission.source.byte_length,
                    ),
                ),
            )
            derivation_reused = parser_reused and previous_document is not None
            if derivation_reused:
                assert previous_document is not None
                mappings = previous_document.mappings
            else:
                mappings = build_document_span_mappings(content, parsed)
            if (
                derivation_reused
                and previous_snapshot is not None
                and previous_snapshot.configuration.chunking_policy
                == request.configuration.chunking_policy
            ):
                assert previous_document is not None
                chunks = previous_document.chunks
            else:
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
        return CanonicalCorpusPreparation(
            request.configuration,
            tuple(documents),
            tuple(rejections),
            discovery,
            tuple(ocr_required),
            corpus_lock,
        )

    def ingest(self, request: CanonicalIngestRequest) -> CanonicalIngestResult:
        """Preserve the one-call installed API over distinct internal operations."""
        previous_snapshot = self._previous_snapshot(request)
        preparation = self.prepare(request, previous_snapshot=previous_snapshot)
        snapshot = preparation.snapshot()
        delta = (
            plan_corpus_delta(previous_snapshot, snapshot)
            if previous_snapshot is not None
            else None
        )
        disposition: IngestDisposition = (
            "initial"
            if previous_snapshot is None
            else "unchanged"
            if previous_snapshot.snapshot_id == snapshot.snapshot_id
            else "changed"
        )
        publication = (
            publish_corpus_snapshot(request.publication_root, snapshot)
            if request.publication_root is not None
            else None
        )
        return CanonicalIngestResult(
            snapshot,
            preparation.discovery,
            preparation.ocr_required,
            publication,
            preparation.corpus_lock,
            disposition,
            delta,
        )


def ingest_corpus(request: CanonicalIngestRequest) -> CanonicalIngestResult:
    """Run canonical ingestion through the default installed runtime adapter."""

    return CanonicalIngestRuntime().ingest(request)


def prepare_corpus(request: CanonicalIngestRequest) -> CanonicalCorpusPreparation:
    """Run only the source-document operation for Runtime composition."""
    return CanonicalIngestRuntime().prepare(request)


__all__ = [
    "CanonicalIngestError",
    "CanonicalIngestRequest",
    "CanonicalIngestResult",
    "CanonicalIngestRuntime",
    "CanonicalCorpusPreparation",
    "CanonicalRetainedSource",
    "CorpusDiscoveryLimits",
    "CorpusSnapshotConfiguration",
    "assemble_corpus_snapshot_manifest",
    "ingest_corpus",
    "prepare_corpus",
]
