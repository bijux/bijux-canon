# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Verify exact citation integrity and conservatively classify entailment."""

from __future__ import annotations

from enum import StrEnum
import hashlib
import re
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_linking import (
    ClaimCitationLink,
    ClaimCitationSet,
)
from bijux_canon_reason.grounding.claim_normalization import (
    AtomicClaim,
    NormalizedClaimSet,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)

_WORD = re.compile(r"[^\W_]+", flags=re.UNICODE)
_NEGATIONS = frozenset({"no", "not", "never", "neither", "nor", "without"})
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "did",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
)


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


class CitationVerificationError(ValueError):
    """Citation verification inputs are inconsistent or corrupt."""

    def __init__(self, code: CitationVerificationErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class CitationVerificationPolicy(StableModel):
    """Versioned deterministic thresholds for conservative entailment."""

    schema_version: str = "bijux.canon.reason.citation_verification_policy.v1"
    minimum_evidence_terms: int = 2
    related_claim_term_coverage: float = 0.6
    opposition_claim_term_coverage: float = 0.8

    @model_validator(mode="after")
    def _validate_policy(self) -> Self:
        if self.minimum_evidence_terms <= 0:
            raise ValueError("minimum evidence terms must be positive")
        if not 0 < self.related_claim_term_coverage <= 1:
            raise ValueError("related claim coverage must be within (0, 1]")
        if not 0 < self.opposition_claim_term_coverage <= 1:
            raise ValueError("opposition claim coverage must be within (0, 1]")
        if self.opposition_claim_term_coverage < self.related_claim_term_coverage:
            raise ValueError(
                "opposition coverage cannot be weaker than related coverage"
            )
        return self

    @property
    def artifact_id(self) -> str:
        """Return the immutable policy identity."""

        return content_artifact_id(self.model_dump(mode="json"))


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

    schema_version: str = "bijux.canon.reason.citation_verification_report.v1"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    policy_artifact_id: str
    outcome: CitationVerificationOutcome
    integrity_verified_links: int
    integrity_total_links: int
    claims: tuple[VerifiedAtomicClaim, ...]

    @field_validator(
        "artifact_id",
        "source_claim_set_artifact_id",
        "claim_citation_set_artifact_id",
        "policy_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
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

    def __init__(self, policy: CitationVerificationPolicy | None = None) -> None:
        self._policy = policy or CitationVerificationPolicy()

    def verify(
        self,
        *,
        claim_set: NormalizedClaimSet,
        citation_set: ClaimCitationSet,
    ) -> CitationVerificationReport:
        """Verify every link and classify its conservative entailment relation."""

        if citation_set.source_claim_set_artifact_id != claim_set.artifact_id:
            raise CitationVerificationError(
                CitationVerificationErrorCode.claim_set_mismatch,
                "citation links reference a different normalized claim set",
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
                self._assess(claim, link) for link in links_by_claim[claim.artifact_id]
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
            "schema_version": "bijux.canon.reason.citation_verification_report.v1",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
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
            policy_artifact_id=self._policy.artifact_id,
            outcome=outcome,
            integrity_verified_links=integrity_count,
            integrity_total_links=len(citation_set.links),
            claims=tuple(verified_claims),
        )

    def _assess(
        self, claim: AtomicClaim, link: ClaimCitationLink
    ) -> EvidenceEntailmentAssessment:
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
        claim_words = _terms(claim.statement)
        evidence_words = _terms(link.exact_text)
        exact_span = claim.statement in link.exact_text
        claim_negated = _negated(claim.statement)
        evidence_negated = _negated(link.exact_text)
        coverage = (
            len(claim_words & evidence_words) / len(claim_words) if claim_words else 0.0
        )
        if len(evidence_words) < self._policy.minimum_evidence_terms:
            verdict = EntailmentVerdict.insufficiency
            rationale = "evidence_below_minimum_terms"
        elif exact_span:
            verdict = EntailmentVerdict.direct_support
            rationale = "claim_is_exact_evidence_span"
        elif (
            coverage >= self._policy.opposition_claim_term_coverage
            and claim_negated is not evidence_negated
        ):
            verdict = EntailmentVerdict.opposition
            rationale = "high_overlap_with_opposite_negation"
        elif coverage >= self._policy.related_claim_term_coverage:
            verdict = EntailmentVerdict.ambiguity
            rationale = "related_but_not_exactly_entailed"
        else:
            verdict = EntailmentVerdict.irrelevance
            rationale = "insufficient_claim_term_overlap"
        payload = {
            "claim_artifact_id": claim.artifact_id,
            "claim_ordinal": claim.ordinal,
            "claim_citation_link_artifact_id": link.artifact_id,
            "citation_evidence_artifact_id": link.citation_evidence_artifact_id,
            "integrity": CitationIntegrityStatus.verified.value,
            "verdict": verdict.value,
            "claim_term_coverage": coverage,
            "exact_claim_span": exact_span,
            "claim_negated": claim_negated,
            "evidence_negated": evidence_negated,
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
            claim_term_coverage=coverage,
            exact_claim_span=exact_span,
            claim_negated=claim_negated,
            evidence_negated=evidence_negated,
            rationale_code=rationale,
        )


def _terms(text: str) -> frozenset[str]:
    return frozenset(
        _stem(word)
        for word in (item.casefold() for item in _WORD.findall(text))
        if word not in _STOP_WORDS and word not in _NEGATIONS
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


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            return word[: -len(suffix)]
    return word


def _negated(text: str) -> bool:
    return bool(
        _NEGATIONS.intersection(item.casefold() for item in _WORD.findall(text))
    )


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
    "VerifiedAtomicClaim",
]
