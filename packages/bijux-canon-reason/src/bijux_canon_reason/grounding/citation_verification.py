# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Verify exact citation integrity and conservatively classify entailment."""

from __future__ import annotations

from enum import StrEnum
import hashlib
from typing import Protocol, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_linking import (
    CitationSourceDescriptor,
    ClaimCitationLink,
    ClaimCitationSet,
)
from bijux_canon_reason.grounding.claim_normalization import (
    AtomicClaim,
    NormalizedClaimSet,
)
from bijux_canon_reason.grounding.evidence_packets import (
    CitationEvidence,
    EvidencePacket,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.grounding.semantic_alignment import (
    assess_conservative_alignment,
)

_STRUCTURED_DECISION_PREFIX = "bijux.canon.reason.structured-entailment-decision.v1:"


class CitationIntegrityStatus(StrEnum):
    """Whether a link retains reachable, internally consistent exact evidence."""

    verified = "verified"


class EntailmentVerdict(StrEnum):
    """Conservative relationship between a claim and exact cited evidence."""

    direct_support = "direct_support"
    opposition = "opposition"
    ambiguity = "ambiguity"
    irrelevance = "irrelevance"
    insufficiency = "insufficiency"


class CitationVerificationOutcome(StrEnum):
    """Whether the input exposed any claims requiring verification."""

    claims_verified = "claims_verified"
    no_claims = "no_claims"


class CitationVerificationErrorCode(StrEnum):
    """Stable fail-closed verification input errors."""

    claim_set_mismatch = "claim_set_mismatch"
    claim_identity_mismatch = "claim_identity_mismatch"
    integrity_failure = "integrity_failure"
    evidence_packet_mismatch = "evidence_packet_mismatch"
    evidence_identity_mismatch = "evidence_identity_mismatch"
    source_identity_mismatch = "source_identity_mismatch"
    structured_decision_invalid = "structured_decision_invalid"


class CitationVerificationError(ValueError):
    """Citation verification inputs are inconsistent or corrupt."""

    def __init__(self, code: CitationVerificationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class CitationVerificationPolicy(StableModel):
    """Versioned deterministic thresholds for conservative entailment."""

    schema_version: str = "bijux.canon.reason.citation_verification_policy.v2"
    minimum_evidence_terms: int = 2
    related_claim_term_coverage: float = 0.6
    support_claim_term_coverage: float = 0.9
    opposition_claim_term_coverage: float = 0.8
    structured_minimum_confidence: float = 0.95

    @model_validator(mode="after")
    def _validate_policy(self) -> Self:
        if self.minimum_evidence_terms <= 0:
            raise ValueError("minimum evidence terms must be positive")
        if not 0 < self.related_claim_term_coverage <= 1:
            raise ValueError("related claim coverage must be within (0, 1]")
        if not 0 < self.opposition_claim_term_coverage <= 1:
            raise ValueError("opposition claim coverage must be within (0, 1]")
        if not 0 < self.support_claim_term_coverage <= 1:
            raise ValueError("support claim coverage must be within (0, 1]")
        if self.support_claim_term_coverage < self.related_claim_term_coverage:
            raise ValueError("support coverage cannot be weaker than related coverage")
        if self.opposition_claim_term_coverage < self.related_claim_term_coverage:
            raise ValueError(
                "opposition coverage cannot be weaker than related coverage"
            )
        if not 0 < self.structured_minimum_confidence <= 1:
            raise ValueError("structured confidence must be within (0, 1]")
        return self

    @property
    def artifact_id(self) -> str:
        """Return the immutable policy identity."""

        return content_artifact_id(self.model_dump(mode="json"))


class StructuredEntailmentDecision(StableModel):
    """Typed optional semantic-verifier decision bound to exact inputs."""

    schema_version: str = "bijux.canon.reason.structured_entailment_decision.v1"
    artifact_id: str
    verifier_id: str
    verifier_configuration_artifact_id: str
    claim_artifact_id: str
    claim_citation_link_artifact_id: str
    verdict: EntailmentVerdict
    confidence: float
    entity_alignment: bool
    scope_alignment: bool
    negation_alignment: bool
    qualifier_alignment: bool
    rationale_code: str

    @classmethod
    def create(
        cls,
        *,
        verifier_id: str,
        verifier_configuration_artifact_id: str,
        claim_artifact_id: str,
        claim_citation_link_artifact_id: str,
        verdict: EntailmentVerdict,
        confidence: float,
        entity_alignment: bool,
        scope_alignment: bool,
        negation_alignment: bool,
        qualifier_alignment: bool,
        rationale_code: str,
    ) -> Self:
        payload = {
            "schema_version": "bijux.canon.reason.structured_entailment_decision.v1",
            "verifier_id": verifier_id,
            "verifier_configuration_artifact_id": verifier_configuration_artifact_id,
            "claim_artifact_id": claim_artifact_id,
            "claim_citation_link_artifact_id": claim_citation_link_artifact_id,
            "verdict": verdict.value,
            "confidence": confidence,
            "entity_alignment": entity_alignment,
            "scope_alignment": scope_alignment,
            "negation_alignment": negation_alignment,
            "qualifier_alignment": qualifier_alignment,
            "rationale_code": rationale_code,
        }
        return cls(
            artifact_id=content_artifact_id(payload),
            verifier_id=verifier_id,
            verifier_configuration_artifact_id=verifier_configuration_artifact_id,
            claim_artifact_id=claim_artifact_id,
            claim_citation_link_artifact_id=claim_citation_link_artifact_id,
            verdict=verdict,
            confidence=confidence,
            entity_alignment=entity_alignment,
            scope_alignment=scope_alignment,
            negation_alignment=negation_alignment,
            qualifier_alignment=qualifier_alignment,
            rationale_code=rationale_code,
        )

    @field_validator(
        "artifact_id",
        "verifier_configuration_artifact_id",
        "claim_artifact_id",
        "claim_citation_link_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("verifier_id", "rationale_code")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "structured verifier identity and rationale cannot be empty"
            )
        return value

    @model_validator(mode="after")
    def _validate_decision(self) -> Self:
        if not 0 <= self.confidence <= 1:
            raise ValueError("structured verifier confidence must be within [0, 1]")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("structured entailment decision identity does not match")
        return self


class StructuredEntailmentVerifier(Protocol):
    """Optional bounded semantic verifier for deterministically unresolved links."""

    def assess(
        self, *, claim: AtomicClaim, citation: ClaimCitationLink
    ) -> StructuredEntailmentDecision:
        """Return one typed decision for the exact claim-citation pair."""


class EvidenceEntailmentAssessment(StableModel):
    """Integrity and entailment result for one claim-citation link."""

    artifact_id: str
    claim_artifact_id: str
    claim_ordinal: int
    claim_citation_link_artifact_id: str
    citation_evidence_artifact_id: str
    integrity: CitationIntegrityStatus
    verdict: EntailmentVerdict
    claim_term_coverage: float
    exact_claim_span: bool
    claim_negated: bool
    evidence_negated: bool
    rationale_code: str

    @property
    def structured_decision(self) -> StructuredEntailmentDecision | None:
        """Decode the optional typed semantic decision retained in the rationale."""

        if not self.rationale_code.startswith(_STRUCTURED_DECISION_PREFIX):
            return None
        return StructuredEntailmentDecision.model_validate_json(
            self.rationale_code.removeprefix(_STRUCTURED_DECISION_PREFIX)
        )

    @field_validator(
        "artifact_id",
        "claim_artifact_id",
        "claim_citation_link_artifact_id",
        "citation_evidence_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("rationale_code")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("entailment rationale code must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_assessment(self) -> Self:
        if self.claim_ordinal <= 0 or not 0 <= self.claim_term_coverage <= 1:
            raise ValueError("entailment assessment measures are invalid")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("entailment assessment identity does not match")
        return self


class VerifiedAtomicClaim(StableModel):
    """Aggregate deterministic verdict for one normalized atomic claim."""

    artifact_id: str
    claim_artifact_id: str
    claim_ordinal: int
    verdict: EntailmentVerdict
    assessments: tuple[EvidenceEntailmentAssessment, ...]

    @field_validator("artifact_id", "claim_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_claim(self) -> Self:
        if self.claim_ordinal <= 0 or not self.assessments:
            raise ValueError("verified claims require evidence assessments")
        if any(
            item.claim_artifact_id != self.claim_artifact_id
            or item.claim_ordinal != self.claim_ordinal
            for item in self.assessments
        ):
            raise ValueError("verified claim assessments reference another claim")
        if self.verdict is not _aggregate_verdict(
            tuple(item.verdict for item in self.assessments)
        ):
            raise ValueError("verified claim aggregate verdict does not match")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("verified claim identity does not match")
        return self


class CitationVerificationReport(StableModel):
    """Complete restart-safe integrity and entailment verification report."""

    schema_version: str = "bijux.canon.reason.citation_verification_report.v2"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    evidence_packet_artifact_id: str
    source_descriptor_artifact_ids: tuple[str, ...]
    policy_artifact_id: str
    outcome: CitationVerificationOutcome
    integrity_verified_links: int
    integrity_total_links: int
    claims: tuple[VerifiedAtomicClaim, ...]

    @field_validator(
        "artifact_id",
        "source_claim_set_artifact_id",
        "claim_citation_set_artifact_id",
        "evidence_packet_artifact_id",
        "policy_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        if len(self.source_descriptor_artifact_ids) != len(
            set(self.source_descriptor_artifact_ids)
        ) or any(
            require_artifact_id(item) != item
            for item in self.source_descriptor_artifact_ids
        ):
            raise ValueError("citation source authority identities must be unique")
        if (
            self.integrity_verified_links < 0
            or self.integrity_total_links < 0
            or self.integrity_verified_links != self.integrity_total_links
        ):
            raise ValueError("citation integrity coverage must be complete")
        if self.outcome is CitationVerificationOutcome.claims_verified:
            if not self.claims:
                raise ValueError("claims_verified outcome requires verified claims")
        elif self.claims or self.integrity_total_links:
            raise ValueError("no_claims outcome cannot contain verification results")
        if tuple(claim.claim_ordinal for claim in self.claims) != tuple(
            range(1, len(self.claims) + 1)
        ):
            raise ValueError("verified claim ordinals must be contiguous")
        if sum(len(claim.assessments) for claim in self.claims) != (
            self.integrity_total_links
        ):
            raise ValueError("verification link coverage is incomplete")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("citation verification report identity does not match")
        return self


class DeterministicCitationVerifier:
    """Verify link integrity and classify only deterministic textual evidence."""

    def __init__(
        self,
        policy: CitationVerificationPolicy | None = None,
        *,
        structured_verifier: StructuredEntailmentVerifier | None = None,
    ) -> None:
        self._policy = policy or CitationVerificationPolicy()
        self._structured_verifier = structured_verifier

    def verify(
        self,
        *,
        claim_set: NormalizedClaimSet,
        citation_set: ClaimCitationSet,
        evidence_packet: EvidencePacket,
        sources: tuple[CitationSourceDescriptor, ...],
    ) -> CitationVerificationReport:
        """Verify every link and classify its conservative entailment relation."""

        if citation_set.source_claim_set_artifact_id != claim_set.artifact_id:
            raise CitationVerificationError(
                CitationVerificationErrorCode.claim_set_mismatch,
                "citation links reference a different normalized claim set",
            )
        if citation_set.evidence_packet_artifact_id != evidence_packet.artifact_id:
            raise CitationVerificationError(
                CitationVerificationErrorCode.evidence_packet_mismatch,
                "citation links reference a different evidence packet",
            )
        evidence_by_id = {
            evidence.artifact_id: evidence for evidence in evidence_packet.selected
        }
        if len(evidence_by_id) != len(evidence_packet.selected):
            raise CitationVerificationError(
                CitationVerificationErrorCode.evidence_identity_mismatch,
                "evidence authority contains duplicate identities",
            )
        ordered_sources = tuple(sorted(sources, key=lambda source: source.source_id))
        sources_by_id = {source.source_id: source for source in ordered_sources}
        if len(sources_by_id) != len(sources):
            raise CitationVerificationError(
                CitationVerificationErrorCode.source_identity_mismatch,
                "citation source authority contains duplicate identities",
            )
        claim_ids = tuple(claim.artifact_id for claim in claim_set.claims)
        if citation_set.claim_artifact_ids != claim_ids:
            raise CitationVerificationError(
                CitationVerificationErrorCode.claim_identity_mismatch,
                "citation links do not cover the supplied normalized claim identities",
            )
        links_by_claim: dict[str, list[ClaimCitationLink]] = {
            claim_id: [] for claim_id in claim_ids
        }
        for link in citation_set.links:
            links_by_claim[link.claim_artifact_id].append(link)

        verified_claims = []
        integrity_count = 0
        for claim in claim_set.claims:
            assessments = tuple(
                self._assess(
                    claim,
                    link,
                    evidence_by_id=evidence_by_id,
                    sources_by_id=sources_by_id,
                )
                for link in links_by_claim[claim.artifact_id]
            )
            integrity_count += len(assessments)
            verdict = _aggregate_verdict(tuple(item.verdict for item in assessments))
            payload = {
                "claim_artifact_id": claim.artifact_id,
                "claim_ordinal": claim.ordinal,
                "verdict": verdict.value,
                "assessments": tuple(
                    item.model_dump(mode="json") for item in assessments
                ),
            }
            verified_claims.append(
                VerifiedAtomicClaim(
                    artifact_id=content_artifact_id(payload),
                    claim_artifact_id=claim.artifact_id,
                    claim_ordinal=claim.ordinal,
                    verdict=verdict,
                    assessments=assessments,
                )
            )
        outcome = (
            CitationVerificationOutcome.claims_verified
            if verified_claims
            else CitationVerificationOutcome.no_claims
        )
        payload = {
            "schema_version": "bijux.canon.reason.citation_verification_report.v2",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
            "evidence_packet_artifact_id": evidence_packet.artifact_id,
            "source_descriptor_artifact_ids": tuple(
                source.artifact_id for source in ordered_sources
            ),
            "policy_artifact_id": self._policy.artifact_id,
            "outcome": outcome.value,
            "integrity_verified_links": integrity_count,
            "integrity_total_links": len(citation_set.links),
            "claims": tuple(claim.model_dump(mode="json") for claim in verified_claims),
        }
        return CitationVerificationReport(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=claim_set.artifact_id,
            claim_citation_set_artifact_id=citation_set.artifact_id,
            evidence_packet_artifact_id=evidence_packet.artifact_id,
            source_descriptor_artifact_ids=tuple(
                source.artifact_id for source in ordered_sources
            ),
            policy_artifact_id=self._policy.artifact_id,
            outcome=outcome,
            integrity_verified_links=integrity_count,
            integrity_total_links=len(citation_set.links),
            claims=tuple(verified_claims),
        )

    def _assess(
        self,
        claim: AtomicClaim,
        link: ClaimCitationLink,
        *,
        evidence_by_id: dict[str, CitationEvidence],
        sources_by_id: dict[str, CitationSourceDescriptor],
    ) -> EvidenceEntailmentAssessment:
        evidence = evidence_by_id.get(link.citation_evidence_artifact_id)
        if evidence is None or not _link_matches_evidence(link, evidence):
            raise CitationVerificationError(
                CitationVerificationErrorCode.evidence_identity_mismatch,
                "claim citation does not match its authoritative evidence record",
            )
        source = sources_by_id.get(link.source_id)
        if source is None or not _link_matches_source(link, source):
            raise CitationVerificationError(
                CitationVerificationErrorCode.source_identity_mismatch,
                "claim citation does not match its authoritative source metadata",
            )
        if (
            link.claim_artifact_id != claim.artifact_id
            or link.claim_ordinal != claim.ordinal
            or hashlib.sha256(link.exact_text.encode()).hexdigest()
            != link.exact_text_sha256
            or not _locator_reachable(link)
        ):
            raise CitationVerificationError(
                CitationVerificationErrorCode.integrity_failure,
                "claim citation integrity verification failed",
            )
        semantic = assess_conservative_alignment(
            claim=claim.statement,
            evidence=link.exact_text,
            minimum_evidence_terms=self._policy.minimum_evidence_terms,
            related_claim_term_coverage=self._policy.related_claim_term_coverage,
            support_claim_term_coverage=self._policy.support_claim_term_coverage,
            opposition_claim_term_coverage=(
                self._policy.opposition_claim_term_coverage
            ),
        )
        verdict = EntailmentVerdict(semantic.relation.value)
        rationale = semantic.rationale_code
        if self._structured_verifier is not None and verdict in {
            EntailmentVerdict.ambiguity,
            EntailmentVerdict.irrelevance,
            EntailmentVerdict.insufficiency,
        }:
            decision = self._structured_verifier.assess(claim=claim, citation=link)
            if (
                decision.claim_artifact_id != claim.artifact_id
                or decision.claim_citation_link_artifact_id != link.artifact_id
            ):
                raise CitationVerificationError(
                    CitationVerificationErrorCode.structured_decision_invalid,
                    "structured verifier decision references different inputs",
                )
            verdict = _structured_verdict(decision, self._policy)
            rationale = _encode_structured_decision(decision)
        payload = {
            "claim_artifact_id": claim.artifact_id,
            "claim_ordinal": claim.ordinal,
            "claim_citation_link_artifact_id": link.artifact_id,
            "citation_evidence_artifact_id": link.citation_evidence_artifact_id,
            "integrity": CitationIntegrityStatus.verified.value,
            "verdict": verdict.value,
            "claim_term_coverage": semantic.claim_term_coverage,
            "exact_claim_span": semantic.exact_claim_span,
            "claim_negated": semantic.claim_negated,
            "evidence_negated": semantic.evidence_negated,
            "rationale_code": rationale,
        }
        return EvidenceEntailmentAssessment(
            artifact_id=content_artifact_id(payload),
            claim_artifact_id=claim.artifact_id,
            claim_ordinal=claim.ordinal,
            claim_citation_link_artifact_id=link.artifact_id,
            citation_evidence_artifact_id=link.citation_evidence_artifact_id,
            integrity=CitationIntegrityStatus.verified,
            verdict=verdict,
            claim_term_coverage=semantic.claim_term_coverage,
            exact_claim_span=semantic.exact_claim_span,
            claim_negated=semantic.claim_negated,
            evidence_negated=semantic.evidence_negated,
            rationale_code=rationale,
        )


def _structured_verdict(
    decision: StructuredEntailmentDecision, policy: CitationVerificationPolicy
) -> EntailmentVerdict:
    if decision.confidence < policy.structured_minimum_confidence:
        return EntailmentVerdict.ambiguity
    shared_alignment = (
        decision.entity_alignment
        and decision.scope_alignment
        and decision.qualifier_alignment
    )
    if (
        decision.verdict is EntailmentVerdict.direct_support
        and shared_alignment
        and decision.negation_alignment
    ):
        return EntailmentVerdict.direct_support
    if (
        decision.verdict is EntailmentVerdict.opposition
        and shared_alignment
        and not decision.negation_alignment
    ):
        return EntailmentVerdict.opposition
    if decision.verdict in {
        EntailmentVerdict.irrelevance,
        EntailmentVerdict.insufficiency,
    }:
        return decision.verdict
    return EntailmentVerdict.ambiguity


def _encode_structured_decision(decision: StructuredEntailmentDecision) -> str:
    return _STRUCTURED_DECISION_PREFIX + decision.model_dump_json()


def _link_matches_evidence(link: ClaimCitationLink, evidence: CitationEvidence) -> bool:
    """Compare every citation-bearing evidence coordinate to its closed authority."""

    return (
        link.document_id == evidence.document_id
        and link.chunk_artifact_id == evidence.chunk_artifact_id
        and link.retrieval_artifact_id == evidence.retrieval_artifact_id
        and link.source_id == evidence.source_id
        and link.source_artifact_id == evidence.locator.source_artifact_id
        and link.source_uri == evidence.locator.source_uri
        and link.source_content_sha256 == evidence.locator.source_content_sha256
        and link.section_path == evidence.section_path
        and link.locator_artifact_id == evidence.locator.artifact_id
        and link.locator_scheme == evidence.locator.scheme
        and link.locator_selectors == evidence.locator.selectors
        and link.exact_text == evidence.exact_text
        and link.exact_text_sha256 == evidence.exact_text_sha256
    )


def _link_matches_source(
    link: ClaimCitationLink, source: CitationSourceDescriptor
) -> bool:
    """Compare complete bibliographic and provenance data to its closed authority."""

    return (
        link.source_descriptor_artifact_id == source.artifact_id
        and link.source_id == source.source_id
        and link.source_title == source.title
        and link.source_authors == source.authors
        and link.source_journal == source.journal
        and link.source_publication_date == source.publication_date
        and link.source_doi == source.doi
        and link.source_uri == source.canonical_uri
        and link.source_content_sha256 == source.source_content_sha256
        and link.source_license_expression == source.license_expression
        and link.source_license_url == source.license_url
        and link.source_provenance_artifact_id == source.provenance_artifact_id
        and link.source_format_id == source.format_id
        and link.source_language == source.language
    )


def _locator_reachable(link: ClaimCitationLink) -> bool:
    selectors = dict(link.locator_selectors)
    span_reachable = False
    for start_name, end_name in (
        ("char_start", "char_end"),
        ("text_start", "text_end"),
        ("byte_start", "byte_end"),
    ):
        if start_name in selectors or end_name in selectors:
            start = selectors.get(start_name)
            end = selectors.get(end_name)
            if (
                not isinstance(start, int)
                or isinstance(start, bool)
                or not isinstance(end, int)
                or isinstance(end, bool)
                or start < 0
                or end <= start
            ):
                return False
            span_reachable = True
    structural = {
        "block_index",
        "dom_path",
        "element_path",
        "line_start",
        "page_number",
        "paragraph_number",
        "window_ordinal",
    }
    return span_reachable or bool(structural.intersection(selectors))


def _aggregate_verdict(
    verdicts: tuple[EntailmentVerdict, ...],
) -> EntailmentVerdict:
    if not verdicts:
        return EntailmentVerdict.insufficiency
    values = set(verdicts)
    if {
        EntailmentVerdict.direct_support,
        EntailmentVerdict.opposition,
    }.issubset(values):
        return EntailmentVerdict.ambiguity
    for verdict in (
        EntailmentVerdict.direct_support,
        EntailmentVerdict.opposition,
        EntailmentVerdict.ambiguity,
        EntailmentVerdict.irrelevance,
        EntailmentVerdict.insufficiency,
    ):
        if verdict in values:
            return verdict
    raise AssertionError("unreachable entailment aggregate")


__all__ = [
    "CitationIntegrityStatus",
    "CitationVerificationError",
    "CitationVerificationErrorCode",
    "CitationVerificationOutcome",
    "CitationVerificationPolicy",
    "CitationVerificationReport",
    "DeterministicCitationVerifier",
    "EntailmentVerdict",
    "EvidenceEntailmentAssessment",
    "StructuredEntailmentDecision",
    "StructuredEntailmentVerifier",
    "VerifiedAtomicClaim",
]
