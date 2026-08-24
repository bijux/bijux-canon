# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Deduplicate and render human-usable exact citations."""

from __future__ import annotations

import hashlib
import json
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_linking import (
    ClaimCitationLink,
    ClaimCitationSet,
    LocatorValue,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)


class PresentedCitation(StableModel):
    """One deduplicated bibliography, locator, and exact-quote record."""

    schema_version: str = "bijux.canon.reason.presented_citation.v1"
    artifact_id: str
    number: int
    citation_evidence_artifact_id: str
    claim_artifact_ids: tuple[str, ...]
    document_id: str
    chunk_artifact_id: str
    retrieval_artifact_id: str
    source_descriptor_artifact_id: str
    source_id: str
    title: str
    authors: tuple[str, ...]
    journal: str | None
    publication_date: str | None
    doi: str | None
    source_uri: str
    source_artifact_id: str
    source_content_sha256: str
    license_expression: str | None
    license_url: str | None
    provenance_artifact_id: str | None
    format_id: str | None
    language: str | None
    section_path: tuple[str, ...]
    locator_artifact_id: str
    locator_scheme: str
    locator_selectors: tuple[tuple[str, LocatorValue], ...]
    exact_quote: str
    exact_quote_sha256: str

    @field_validator(
        "artifact_id",
        "citation_evidence_artifact_id",
        "chunk_artifact_id",
        "retrieval_artifact_id",
        "source_descriptor_artifact_id",
        "source_artifact_id",
        "locator_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_ids")
    @classmethod
    def _validate_claim_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("presented citation claim identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("source_content_sha256", "exact_quote_sha256")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        return require_sha256(value)

    @model_validator(mode="after")
    def _validate_entry(self) -> Self:
        if self.number <= 0:
            raise ValueError("presented citation number must be positive")
        if (
            not self.exact_quote
            or not self.section_path
            or not self.title.strip()
            or not self.source_id.strip()
            or hashlib.sha256(self.exact_quote.encode()).hexdigest()
            != self.exact_quote_sha256
        ):
            raise ValueError("presented citation requires an exact quote and section")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("presented citation identity does not match")
        return self


class CitationPresentation(StableModel):
    """Complete deterministic display records for one exact citation set."""

    schema_version: str = "bijux.canon.reason.citation_presentation.v1"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    entries: tuple[PresentedCitation, ...]

    @field_validator(
        "artifact_id", "source_claim_set_artifact_id", "claim_citation_set_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_presentation(self) -> Self:
        if tuple(entry.number for entry in self.entries) != tuple(
            range(1, len(self.entries) + 1)
        ):
            raise ValueError("presented citation numbers must be contiguous")
        evidence_ids = tuple(
            entry.citation_evidence_artifact_id for entry in self.entries
        )
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("presented citations must deduplicate evidence")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("citation presentation identity does not match")
        return self

    def number_for(self, citation_evidence_artifact_id: str) -> int:
        """Return the stable display number for one exact evidence identity."""

        for entry in self.entries:
            if entry.citation_evidence_artifact_id == citation_evidence_artifact_id:
                return entry.number
        raise ValueError("citation presentation is missing referenced evidence")


class CitationPresentationService:
    """Collapse duplicate claim links without losing multi-claim lineage."""

    def present(self, citation_set: ClaimCitationSet) -> CitationPresentation:
        """Create numbered exact citations in first-link deterministic order."""

        grouped: dict[str, list[ClaimCitationLink]] = {}
        for link in citation_set.links:
            grouped.setdefault(link.citation_evidence_artifact_id, []).append(link)
        entries = []
        for number, links in enumerate(grouped.values(), start=1):
            first = links[0]
            if any(not _same_evidence(first, link) for link in links[1:]):
                raise ValueError("duplicate citation identity has divergent evidence")
            claim_ids = tuple(dict.fromkeys(link.claim_artifact_id for link in links))
            payload = _entry_payload(number=number, link=first, claim_ids=claim_ids)
            entries.append(
                PresentedCitation.model_validate(
                    {"artifact_id": content_artifact_id(payload), **payload}
                )
            )
        payload = {
            "schema_version": "bijux.canon.reason.citation_presentation.v1",
            "source_claim_set_artifact_id": citation_set.source_claim_set_artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
            "entries": tuple(entry.model_dump(mode="json") for entry in entries),
        }
        return CitationPresentation(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=citation_set.source_claim_set_artifact_id,
            claim_citation_set_artifact_id=citation_set.artifact_id,
            entries=tuple(entries),
        )


def render_citation_reference(entry: PresentedCitation) -> str:
    """Render one complete citation without hiding machine-verifiable identities."""

    bibliography = []
    if entry.authors:
        bibliography.append(", ".join(entry.authors))
    bibliography.append(entry.title)
    if entry.journal:
        bibliography.append(entry.journal)
    if entry.publication_date:
        bibliography.append(entry.publication_date)
    if entry.doi:
        bibliography.append(f"doi:{entry.doi}")
    locator = ", ".join(f"{name}={value}" for name, value in entry.locator_selectors)
    details = [
        f"[{entry.number}] " + ". ".join(bibliography) + ".",
        f"Source: {entry.source_uri}",
        f"Section: {' / '.join(entry.section_path)}",
        f"Locator: {entry.locator_scheme}({locator})",
        (
            "Exact quote "
            f"(sha256:{entry.exact_quote_sha256}): "
            f"{json.dumps(entry.exact_quote, ensure_ascii=False)}"
        ),
        f"Source SHA-256: {entry.source_content_sha256}",
        f"Document: {entry.document_id}",
        f"Chunk: {entry.chunk_artifact_id}",
    ]
    if entry.license_expression:
        license_text = entry.license_expression
        if entry.license_url:
            license_text += f" ({entry.license_url})"
        details.append(f"License: {license_text}")
    if entry.provenance_artifact_id:
        details.append(f"Metadata provenance: {entry.provenance_artifact_id}")
    if entry.format_id:
        details.append(f"Format: {entry.format_id}")
    if entry.language:
        details.append(f"Language: {entry.language}")
    return "\n  ".join(details)


def _entry_payload(
    *, number: int, link: ClaimCitationLink, claim_ids: tuple[str, ...]
) -> dict[str, object]:
    return {
        "schema_version": "bijux.canon.reason.presented_citation.v1",
        "number": number,
        "citation_evidence_artifact_id": link.citation_evidence_artifact_id,
        "claim_artifact_ids": claim_ids,
        "document_id": link.document_id,
        "chunk_artifact_id": link.chunk_artifact_id,
        "retrieval_artifact_id": link.retrieval_artifact_id,
        "source_descriptor_artifact_id": link.source_descriptor_artifact_id,
        "source_id": link.source_id,
        "title": link.source_title,
        "authors": link.source_authors,
        "journal": link.source_journal,
        "publication_date": link.source_publication_date,
        "doi": link.source_doi,
        "source_uri": link.source_uri,
        "source_artifact_id": link.source_artifact_id,
        "source_content_sha256": link.source_content_sha256,
        "license_expression": link.source_license_expression,
        "license_url": link.source_license_url,
        "provenance_artifact_id": link.source_provenance_artifact_id,
        "format_id": link.source_format_id,
        "language": link.source_language,
        "section_path": link.section_path,
        "locator_artifact_id": link.locator_artifact_id,
        "locator_scheme": link.locator_scheme,
        "locator_selectors": link.locator_selectors,
        "exact_quote": link.exact_text,
        "exact_quote_sha256": link.exact_text_sha256,
    }


def _same_evidence(left: ClaimCitationLink, right: ClaimCitationLink) -> bool:
    ignored = {
        "artifact_id",
        "claim_artifact_id",
        "claim_ordinal",
        "citation_ordinal",
        "role",
    }
    return left.model_dump(mode="json", exclude=ignored) == right.model_dump(
        mode="json", exclude=ignored
    )


__all__ = [
    "CitationPresentation",
    "CitationPresentationService",
    "PresentedCitation",
    "render_citation_reference",
]
