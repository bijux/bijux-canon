# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Bind normalized claims to exact, bibliographically identified evidence."""

from __future__ import annotations

from enum import StrEnum
import hashlib
from typing import Self
from urllib.parse import urlparse

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.claim_normalization import (
    AtomicClaimPolarity,
    NormalizedClaimSet,
)
from bijux_canon_reason.grounding.evidence_packets import EvidencePacket
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
    require_sha256,
)

LocatorValue = str | int


class ClaimCitationRole(StrEnum):
    """Candidate evidence relationship before entailment verification."""

    proposed_support = "proposed_support"
    proposed_opposition = "proposed_opposition"
    proposed_ambiguity = "proposed_ambiguity"
    source_observation = "source_observation"


class CitationLinkingErrorCode(StrEnum):
    """Stable fail-closed citation-linking failures."""

    citation_missing = "citation_missing"
    source_metadata_missing = "source_metadata_missing"
    source_metadata_collision = "source_metadata_collision"
    source_identity_mismatch = "source_identity_mismatch"


class CitationLinkingError(ValueError):
    """A claim cannot be bound to complete exact citation metadata."""

    def __init__(self, code: CitationLinkingErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class CitationSourceDescriptor(StableModel):
    """Content-addressed bibliographic identity for one immutable source."""

    schema_version: str = "bijux.canon.reason.citation_source_descriptor.v2"
    artifact_id: str
    source_id: str
    title: str
    canonical_uri: str
    doi: str | None
    source_content_sha256: str
    authors: tuple[str, ...] = ()
    journal: str | None = None
    publication_date: str | None = None
    license_expression: str | None = None
    license_url: str | None = None
    provenance_artifact_id: str | None = None
    format_id: str | None = None
    language: str | None = None

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        title: str,
        canonical_uri: str,
        doi: str | None,
        source_content_sha256: str,
        authors: tuple[str, ...] = (),
        journal: str | None = None,
        publication_date: str | None = None,
        license_expression: str | None = None,
        license_url: str | None = None,
        provenance_artifact_id: str | None = None,
        format_id: str | None = None,
        language: str | None = None,
    ) -> Self:
        """Create a descriptor whose identity covers every bibliographic field."""

        payload = {
            "schema_version": "bijux.canon.reason.citation_source_descriptor.v2",
            "source_id": source_id,
            "title": title,
            "canonical_uri": canonical_uri,
            "doi": doi,
            "source_content_sha256": source_content_sha256,
            "authors": authors,
            "journal": journal,
            "publication_date": publication_date,
            "license_expression": license_expression,
            "license_url": license_url,
            "provenance_artifact_id": provenance_artifact_id,
            "format_id": format_id,
            "language": language,
        }
        return cls(
            artifact_id=content_artifact_id(payload),
            source_id=source_id,
            title=title,
            canonical_uri=canonical_uri,
            doi=doi,
            source_content_sha256=source_content_sha256,
            authors=authors,
            journal=journal,
            publication_date=publication_date,
            license_expression=license_expression,
            license_url=license_url,
            provenance_artifact_id=provenance_artifact_id,
            format_id=format_id,
            language=language,
        )

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("source_content_sha256")
    @classmethod
    def _validate_source_hash(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator("source_id", "title")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("citation source identity and title must not be empty")
        return value

    @field_validator("authors")
    @classmethod
    def _validate_authors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not author.strip() for author in value):
            raise ValueError("citation source authors must not be empty")
        return value

    @field_validator(
        "journal",
        "publication_date",
        "license_expression",
        "license_url",
        "format_id",
        "language",
    )
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("citation source optional metadata must not be empty")
        return value

    @field_validator("provenance_artifact_id")
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("canonical_uri")
    @classmethod
    def _validate_uri(cls, value: str) -> str:
        parsed = urlparse(value)
        is_network_source = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        is_local_content_source = (
            parsed.scheme == "urn"
            and parsed.path.startswith("bijux:source:")
            and len(parsed.path.removeprefix("bijux:source:")) == 64
            and all(
                character in "0123456789abcdef"
                for character in parsed.path.removeprefix("bijux:source:")
            )
        )
        if not (is_network_source or is_local_content_source):
            raise ValueError(
                "citation source URI must be absolute HTTP(S) or a Bijux source URN"
            )
        if parsed.username or parsed.password:
            raise ValueError("citation source URI must not contain credentials")
        return value

    @field_validator("doi")
    @classmethod
    def _validate_doi(cls, value: str | None) -> str | None:
        if value is not None and (
            not value.startswith("10.") or "/" not in value or value.strip() != value
        ):
            raise ValueError("citation DOI must be null or a canonical DOI")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("citation source identity does not match its payload")
        return self


class ClaimCitationLink(StableModel):
    """One exact evidence span linked to one normalized atomic claim."""

    artifact_id: str
    claim_artifact_id: str
    claim_ordinal: int
    citation_ordinal: int
    role: ClaimCitationRole
    citation_evidence_artifact_id: str
    source_descriptor_artifact_id: str
    document_id: str
    chunk_artifact_id: str
    retrieval_artifact_id: str
    source_id: str
    source_title: str
    source_authors: tuple[str, ...]
    source_journal: str | None
    source_publication_date: str | None
    source_doi: str | None
    source_uri: str
    source_artifact_id: str
    source_content_sha256: str
    source_license_expression: str | None
    source_license_url: str | None
    source_provenance_artifact_id: str | None
    source_format_id: str | None
    source_language: str | None
    section_path: tuple[str, ...]
    locator_artifact_id: str
    locator_scheme: str
    locator_selectors: tuple[tuple[str, LocatorValue], ...]
    exact_text: str
    exact_text_sha256: str

    @field_validator(
        "artifact_id",
        "claim_artifact_id",
        "citation_evidence_artifact_id",
        "source_descriptor_artifact_id",
        "chunk_artifact_id",
        "retrieval_artifact_id",
        "source_artifact_id",
        "locator_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("source_content_sha256", "exact_text_sha256")
    @classmethod
    def _validate_hash(cls, value: str) -> str:
        return require_sha256(value)

    @field_validator(
        "source_id",
        "document_id",
        "source_title",
        "source_uri",
        "locator_scheme",
        "exact_text",
    )
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("claim citation fields must not be empty")
        return value

    @field_validator("source_authors")
    @classmethod
    def _validate_source_authors(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not author.strip() for author in value):
            raise ValueError("claim citation source authors must not be empty")
        return value

    @field_validator(
        "source_journal",
        "source_publication_date",
        "source_license_expression",
        "source_license_url",
        "source_format_id",
        "source_language",
    )
    @classmethod
    def _validate_optional_source_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("claim citation optional source fields must not be empty")
        return value

    @field_validator("source_provenance_artifact_id")
    @classmethod
    def _validate_optional_source_artifact(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_link(self) -> Self:
        if self.claim_ordinal <= 0 or self.citation_ordinal <= 0:
            raise ValueError("claim citation ordinals must be positive")
        selector_names = tuple(name for name, _ in self.locator_selectors)
        if (
            not self.section_path
            or any(not part for part in self.section_path)
            or not selector_names
            or any(not name for name in selector_names)
            or len(selector_names) != len(set(selector_names))
        ):
            raise ValueError("claim citation requires section and locator coordinates")
        if hashlib.sha256(self.exact_text.encode()).hexdigest() != (
            self.exact_text_sha256
        ):
            raise ValueError("claim citation exact text digest does not match")
        source = CitationSourceDescriptor.create(
            source_id=self.source_id,
            title=self.source_title,
            canonical_uri=self.source_uri,
            doi=self.source_doi,
            source_content_sha256=self.source_content_sha256,
            authors=self.source_authors,
            journal=self.source_journal,
            publication_date=self.source_publication_date,
            license_expression=self.source_license_expression,
            license_url=self.source_license_url,
            provenance_artifact_id=self.source_provenance_artifact_id,
            format_id=self.source_format_id,
            language=self.source_language,
        )
        if source.artifact_id != self.source_descriptor_artifact_id:
            raise ValueError("claim citation source descriptor identity does not match")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("claim citation identity does not match its payload")
        return self


class ClaimCitationSet(StableModel):
    """Complete content-addressed citation links for a normalized claim set."""

    schema_version: str = "bijux.canon.reason.claim_citation_set.v2"
    artifact_id: str
    source_claim_set_artifact_id: str
    evidence_packet_artifact_id: str
    claim_artifact_ids: tuple[str, ...]
    links: tuple[ClaimCitationLink, ...]

    @field_validator(
        "artifact_id", "source_claim_set_artifact_id", "evidence_packet_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_ids")
    @classmethod
    def _validate_claim_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("claim citation set requires unique claim identities")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_set(self) -> Self:
        pairs = tuple(
            (link.claim_artifact_id, link.citation_evidence_artifact_id)
            for link in self.links
        )
        if len(pairs) != len(set(pairs)):
            raise ValueError("claim citation links must be unique")
        if tuple(
            (link.claim_ordinal, link.citation_ordinal) for link in self.links
        ) != tuple(
            sorted((link.claim_ordinal, link.citation_ordinal) for link in self.links)
        ):
            raise ValueError("claim citation links must have deterministic order")
        linked_claims = {link.claim_artifact_id for link in self.links}
        if linked_claims != set(self.claim_artifact_ids):
            raise ValueError("every normalized claim requires an exact citation link")
        expected_claim_ordinals = {
            claim_id: ordinal
            for ordinal, claim_id in enumerate(self.claim_artifact_ids, start=1)
        }
        for claim_id, claim_ordinal in expected_claim_ordinals.items():
            claim_links = tuple(
                link for link in self.links if link.claim_artifact_id == claim_id
            )
            if any(
                link.claim_ordinal != claim_ordinal for link in claim_links
            ) or tuple(link.citation_ordinal for link in claim_links) != tuple(
                range(1, len(claim_links) + 1)
            ):
                raise ValueError("claim citation ordinals must be contiguous")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("claim citation set identity does not match its payload")
        return self


class ClaimCitationLinker:
    """Resolve each normalized claim citation against a closed evidence packet."""

    def link(
        self,
        *,
        claim_set: NormalizedClaimSet,
        evidence_packet: EvidencePacket,
        sources: tuple[CitationSourceDescriptor, ...],
    ) -> ClaimCitationSet:
        """Attach complete source and exact-span data or fail closed."""

        source_by_id = {source.source_id: source for source in sources}
        if len(source_by_id) != len(sources):
            raise CitationLinkingError(
                CitationLinkingErrorCode.source_metadata_collision,
                "citation source metadata contains duplicate source identities",
            )
        evidence_by_id = {
            evidence.artifact_id: evidence for evidence in evidence_packet.selected
        }
        links: list[ClaimCitationLink] = []
        for claim in claim_set.claims:
            for citation_ordinal, citation_id in enumerate(
                claim.citation_evidence_artifact_ids, start=1
            ):
                evidence = evidence_by_id.get(citation_id)
                if evidence is None:
                    raise CitationLinkingError(
                        CitationLinkingErrorCode.citation_missing,
                        "normalized claim citation is absent from the evidence packet",
                    )
                source = source_by_id.get(evidence.source_id)
                if source is None:
                    raise CitationLinkingError(
                        CitationLinkingErrorCode.source_metadata_missing,
                        "citation source metadata is absent",
                    )
                if (
                    source.canonical_uri != evidence.locator.source_uri
                    or source.source_content_sha256
                    != evidence.locator.source_content_sha256
                ):
                    raise CitationLinkingError(
                        CitationLinkingErrorCode.source_identity_mismatch,
                        "citation source metadata disagrees with the immutable locator",
                    )
                payload = {
                    "claim_artifact_id": claim.artifact_id,
                    "claim_ordinal": claim.ordinal,
                    "citation_ordinal": citation_ordinal,
                    "role": _citation_role(claim.polarity).value,
                    "citation_evidence_artifact_id": evidence.artifact_id,
                    "source_descriptor_artifact_id": source.artifact_id,
                    "document_id": evidence.document_id,
                    "chunk_artifact_id": evidence.chunk_artifact_id,
                    "retrieval_artifact_id": evidence.retrieval_artifact_id,
                    "source_id": source.source_id,
                    "source_title": source.title,
                    "source_authors": source.authors,
                    "source_journal": source.journal,
                    "source_publication_date": source.publication_date,
                    "source_doi": source.doi,
                    "source_uri": source.canonical_uri,
                    "source_artifact_id": evidence.locator.source_artifact_id,
                    "source_content_sha256": source.source_content_sha256,
                    "source_license_expression": source.license_expression,
                    "source_license_url": source.license_url,
                    "source_provenance_artifact_id": source.provenance_artifact_id,
                    "source_format_id": source.format_id,
                    "source_language": source.language,
                    "section_path": evidence.section_path,
                    "locator_artifact_id": evidence.locator.artifact_id,
                    "locator_scheme": evidence.locator.scheme,
                    "locator_selectors": evidence.locator.selectors,
                    "exact_text": evidence.exact_text,
                    "exact_text_sha256": evidence.exact_text_sha256,
                }
                links.append(
                    ClaimCitationLink(
                        artifact_id=content_artifact_id(payload),
                        claim_artifact_id=claim.artifact_id,
                        claim_ordinal=claim.ordinal,
                        citation_ordinal=citation_ordinal,
                        role=_citation_role(claim.polarity),
                        citation_evidence_artifact_id=evidence.artifact_id,
                        source_descriptor_artifact_id=source.artifact_id,
                        document_id=evidence.document_id,
                        chunk_artifact_id=evidence.chunk_artifact_id,
                        retrieval_artifact_id=evidence.retrieval_artifact_id,
                        source_id=source.source_id,
                        source_title=source.title,
                        source_authors=source.authors,
                        source_journal=source.journal,
                        source_publication_date=source.publication_date,
                        source_doi=source.doi,
                        source_uri=source.canonical_uri,
                        source_artifact_id=evidence.locator.source_artifact_id,
                        source_content_sha256=source.source_content_sha256,
                        source_license_expression=source.license_expression,
                        source_license_url=source.license_url,
                        source_provenance_artifact_id=source.provenance_artifact_id,
                        source_format_id=source.format_id,
                        source_language=source.language,
                        section_path=evidence.section_path,
                        locator_artifact_id=evidence.locator.artifact_id,
                        locator_scheme=evidence.locator.scheme,
                        locator_selectors=evidence.locator.selectors,
                        exact_text=evidence.exact_text,
                        exact_text_sha256=evidence.exact_text_sha256,
                    )
                )
        claim_ids = tuple(claim.artifact_id for claim in claim_set.claims)
        payload = {
            "schema_version": "bijux.canon.reason.claim_citation_set.v2",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "evidence_packet_artifact_id": evidence_packet.artifact_id,
            "claim_artifact_ids": claim_ids,
            "links": tuple(link.model_dump(mode="json") for link in links),
        }
        return ClaimCitationSet(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=claim_set.artifact_id,
            evidence_packet_artifact_id=evidence_packet.artifact_id,
            claim_artifact_ids=claim_ids,
            links=tuple(links),
        )


def _citation_role(polarity: AtomicClaimPolarity) -> ClaimCitationRole:
    return {
        AtomicClaimPolarity.supports: ClaimCitationRole.proposed_support,
        AtomicClaimPolarity.opposes: ClaimCitationRole.proposed_opposition,
        AtomicClaimPolarity.ambiguous: ClaimCitationRole.proposed_ambiguity,
        AtomicClaimPolarity.observed: ClaimCitationRole.source_observation,
    }[polarity]


__all__ = [
    "CitationLinkingError",
    "CitationLinkingErrorCode",
    "CitationSourceDescriptor",
    "ClaimCitationLink",
    "ClaimCitationLinker",
    "ClaimCitationRole",
    "ClaimCitationSet",
]
