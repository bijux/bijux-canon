# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical immutable corpus snapshots for admitted ingestion results."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import TypeAlias

from bijux_canon_ingest.domain.document_extraction import (
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
)
from bijux_canon_ingest.domain.semantic_chunking import (
    SemanticChunk,
    SemanticChunkingPolicy,
)
from bijux_canon_ingest.domain.source_admission import AdmissionBudgets, AdmissionResult
from bijux_canon_ingest.domain.source_mapping import NormalizedSpanMapping
from bijux_canon_ingest.domain.source_metadata import CanonicalSourceMetadata

SnapshotParsedDocument: TypeAlias = (
    ParsedDocument
    | ParsedPdfDocument
    | ParsedHtmlDocument
    | ParsedTextDocument
    | ParsedDocxDocument
)

_CORPUS_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


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


@dataclass(frozen=True, slots=True)
class CorpusSnapshotConfiguration:
    """All policies that can affect canonical corpus membership or content."""

    corpus_name: str
    admission_budgets: AdmissionBudgets = AdmissionBudgets()
    chunking_policy: SemanticChunkingPolicy = SemanticChunkingPolicy()

    def __post_init__(self) -> None:
        if _CORPUS_NAME.fullmatch(self.corpus_name) is None:
            raise ValueError(
                "corpus_name must use lowercase portable identifier syntax"
            )

    @property
    def configuration_sha256(self) -> str:
        return _identity(self.manifest())

    def manifest(self) -> dict[str, object]:
        return {
            "admission_budgets": self.admission_budgets.identity_payload(),
            "chunking_policy": self.chunking_policy.manifest(),
            "corpus_name": self.corpus_name,
            "schema_version": "bijux.canon.ingest.corpus_snapshot_configuration.v1",
        }


@dataclass(frozen=True, slots=True)
class CorpusSnapshotDocument:
    """One admitted source and every deterministic artifact derived from it."""

    admission: AdmissionResult
    document: SnapshotParsedDocument
    metadata: CanonicalSourceMetadata
    mappings: tuple[NormalizedSpanMapping, ...]
    chunks: tuple[SemanticChunk, ...]

    def __post_init__(self) -> None:
        source_sha256 = self.admission.source.content_sha256
        if not self.admission.admitted:
            raise ValueError("snapshot documents require admitted sources")
        if self.document.source_content_sha256 != source_sha256:
            raise ValueError(
                "snapshot document extraction has a different source identity"
            )
        if self.metadata.source_content_sha256 != source_sha256:
            raise ValueError(
                "snapshot document metadata has a different source identity"
            )
        if self.metadata.format_id != self.admission.format_id:
            raise ValueError("snapshot metadata format does not match source admission")
        if not self.mappings or not self.chunks:
            raise ValueError("snapshot documents require mappings and chunks")
        if any(
            mapping.source_content_sha256 != source_sha256 for mapping in self.mappings
        ):
            raise ValueError("snapshot mappings have a different source identity")
        if any(chunk.source_content_sha256 != source_sha256 for chunk in self.chunks):
            raise ValueError("snapshot chunks have a different source identity")
        if [chunk.chunk_index for chunk in self.chunks] != list(
            range(len(self.chunks))
        ):
            raise ValueError("snapshot chunks must use contiguous document order")
        mapping_ids = {mapping.mapping_sha256 for mapping in self.mappings}
        if any(
            mapping.mapping_sha256 not in mapping_ids
            and mapping.parent_mapping_sha256 not in mapping_ids
            for chunk in self.chunks
            for mapping in chunk.mappings
        ):
            raise ValueError(
                "snapshot chunk mappings must descend from document mappings"
            )

    @property
    def document_id(self) -> str:
        return _identity(
            {
                "extraction_manifest_sha256": self.document.manifest()[
                    "manifest_sha256"
                ],
                "metadata_manifest_sha256": self.metadata.manifest()["manifest_sha256"],
                "source_content_sha256": self.admission.source.content_sha256,
            }
        )

    def manifest(self) -> dict[str, object]:
        return {
            "admission": self.admission.manifest(),
            "chunks": [chunk.manifest() for chunk in self.chunks],
            "document": self.document.manifest(),
            "document_id": self.document_id,
            "mappings": [mapping.manifest() for mapping in self.mappings],
            "metadata": self.metadata.manifest(),
            "schema_version": "bijux.canon.ingest.corpus_snapshot_document.v1",
        }


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    """A deterministic complete partition of admitted documents and rejections."""

    configuration: CorpusSnapshotConfiguration
    documents: tuple[CorpusSnapshotDocument, ...]
    rejections: tuple[AdmissionResult, ...] = ()

    def __post_init__(self) -> None:
        if not self.documents:
            raise ValueError("corpus snapshot requires at least one admitted document")
        document_order = [
            (
                item.admission.source.root_name,
                item.admission.source.relative_path,
                item.admission.source.content_sha256,
            )
            for item in self.documents
        ]
        rejection_order = [
            (
                item.source.root_name,
                item.source.relative_path,
                item.source.content_sha256,
            )
            for item in self.rejections
        ]
        if document_order != sorted(document_order) or rejection_order != sorted(
            rejection_order
        ):
            raise ValueError(
                "corpus snapshot membership must use canonical source order"
            )
        location_ids = [
            item.admission.source.location_id for item in self.documents
        ] + [item.source.location_id for item in self.rejections]
        if len(location_ids) != len(set(location_ids)):
            raise ValueError("corpus snapshot source locations must be unique")
        if any(rejection.admitted for rejection in self.rejections):
            raise ValueError("corpus snapshot rejections must be rejected outcomes")
        if any(
            document.admission.budgets != self.configuration.admission_budgets
            for document in self.documents
        ) or any(
            rejection.budgets != self.configuration.admission_budgets
            for rejection in self.rejections
        ):
            raise ValueError("snapshot admissions must use its configured budgets")
        if any(
            chunk.chunking_policy_sha256
            != self.configuration.chunking_policy.policy_sha256
            for document in self.documents
            for chunk in document.chunks
        ):
            raise ValueError("snapshot chunks must use its configured chunking policy")

    @property
    def snapshot_id(self) -> str:
        return _identity(self._payload())

    @property
    def canonical_bytes(self) -> bytes:
        """Return the portable newline-terminated canonical snapshot serialization."""

        return _canonical_json(self.manifest()) + b"\n"

    def _payload(self) -> dict[str, object]:
        return {
            "configuration": self.configuration.manifest(),
            "configuration_sha256": self.configuration.configuration_sha256,
            "documents": [document.manifest() for document in self.documents],
            "rejections": [rejection.manifest() for rejection in self.rejections],
            "schema_version": "bijux.canon.ingest.corpus_snapshot.v1",
        }

    def manifest(self) -> dict[str, object]:
        payload = self._payload()
        return {"snapshot_id": _identity(payload), **payload}


__all__ = [
    "CorpusSnapshot",
    "CorpusSnapshotConfiguration",
    "CorpusSnapshotDocument",
    "SnapshotParsedDocument",
]
