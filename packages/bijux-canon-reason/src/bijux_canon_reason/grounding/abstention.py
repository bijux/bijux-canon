# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Admit only verified grounded claims and explain every abstention gap."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_linking import ClaimCitationSet
from bijux_canon_reason.grounding.citation_verification import (
    CitationVerificationReport,
    EntailmentVerdict,
)
from bijux_canon_reason.grounding.claim_normalization import NormalizedClaimSet
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class GroundingRequestStatus(StrEnum):
    """Pre-admission request or evidence condition established upstream."""

    in_scope = "in_scope"
    fabricated_entity = "fabricated_entity"
    out_of_scope = "out_of_scope"
    corrupt_evidence = "corrupt_evidence"


class GroundingAdmissionOutcome(StrEnum):
    """Whether verified claims may reach the grounded answer."""

    admitted = "admitted"
    partially_admitted = "partially_admitted"
    abstained = "abstained"


class EvidenceGapCode(StrEnum):
    """Stable reason and remediation class for an unadmitted claim or request."""

    fabricated_entity = "fabricated_entity"
    out_of_scope = "out_of_scope"
    integrity_failure = "integrity_failure"
    no_retrieved_evidence = "no_retrieved_evidence"
    contradicted_by_evidence = "contradicted_by_evidence"
    ambiguous_evidence = "ambiguous_evidence"
    irrelevant_evidence = "irrelevant_evidence"
    insufficient_evidence = "insufficient_evidence"
    support_coverage_below_policy = "support_coverage_below_policy"


class EvidenceGap(StableModel):
    """One content-addressed evidence deficiency with a concrete next action."""

    artifact_id: str
    code: EvidenceGapCode
    claim_artifact_id: str | None
    detail: str
    required_action: str

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_id")
    @classmethod
    def _validate_claim_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("detail", "required_action")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence gap explanation and action must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("evidence gap identity does not match its payload")
        return self


class RejectedGroundingClaim(StableModel):
    """One normalized claim excluded by deterministic admission policy."""

    claim_artifact_id: str
    verdict: EntailmentVerdict
    evidence_gap_artifact_id: str

    @field_validator("claim_artifact_id", "evidence_gap_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)


class CalibratedAbstentionPolicy(StableModel):
    """Explicit minimum support count and ratio for answer admission."""

    schema_version: str = "bijux.canon.reason.calibrated_abstention_policy.v1"
    minimum_direct_support_claims: int = 1
    minimum_supported_fraction: float = 0.5
    allow_partial_answers: bool = True

    @model_validator(mode="after")
    def _validate_policy(self) -> Self:
        if self.minimum_direct_support_claims <= 0:
            raise ValueError("minimum direct support claims must be positive")
        if not 0 < self.minimum_supported_fraction <= 1:
            raise ValueError("minimum supported fraction must be within (0, 1]")
        return self

    @property
    def artifact_id(self) -> str:
        """Return the immutable admission policy identity."""

        return content_artifact_id(self.model_dump(mode="json"))


class GroundingAdmissionDecision(StableModel):
    """Restart-safe answer admission, rejection, citations, and evidence gaps."""

    schema_version: str = "bijux.canon.reason.grounding_admission_decision.v1"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    verification_report_artifact_id: str | None
    policy_artifact_id: str
    request_status: GroundingRequestStatus
    outcome: GroundingAdmissionOutcome
    admitted_claim_artifact_ids: tuple[str, ...]
    admitted_citation_link_artifact_ids: tuple[str, ...]
    rejected_claims: tuple[RejectedGroundingClaim, ...]
    evidence_gaps: tuple[EvidenceGap, ...]

    @field_validator(
        "artifact_id",
        "source_claim_set_artifact_id",
        "claim_citation_set_artifact_id",
        "policy_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("verification_report_artifact_id")
    @classmethod
    def _validate_report_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator(
        "admitted_claim_artifact_ids", "admitted_citation_link_artifact_ids"
    )
    @classmethod
    def _validate_unique_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("admission identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_decision(self) -> Self:
        if self.outcome is GroundingAdmissionOutcome.abstained:
            if (
                self.admitted_claim_artifact_ids
                or self.admitted_citation_link_artifact_ids
            ):
                raise ValueError("abstention cannot expose claims or citations")
            if not self.evidence_gaps:
                raise ValueError("abstention requires an actionable evidence gap")
        elif (
            not self.admitted_claim_artifact_ids
            or not self.admitted_citation_link_artifact_ids
        ):
            raise ValueError("admission requires claims and their exact citations")
        if self.outcome is GroundingAdmissionOutcome.admitted and self.rejected_claims:
            raise ValueError("complete admission cannot contain rejected claims")
        if (
            self.outcome is GroundingAdmissionOutcome.partially_admitted
            and not self.rejected_claims
        ):
            raise ValueError("partial admission requires rejected claims")
        admitted = set(self.admitted_claim_artifact_ids)
        rejected = {item.claim_artifact_id for item in self.rejected_claims}
        if admitted.intersection(rejected):
            raise ValueError("a claim cannot be both admitted and rejected")
        gap_ids = {gap.artifact_id for gap in self.evidence_gaps}
        if any(
            item.evidence_gap_artifact_id not in gap_ids
            for item in self.rejected_claims
        ):
            raise ValueError("rejected claims require a retained evidence gap")
        if self.request_status is GroundingRequestStatus.corrupt_evidence:
            if self.verification_report_artifact_id is not None:
                raise ValueError("corrupt evidence cannot carry a verified report")
        elif self.verification_report_artifact_id is None:
            raise ValueError("non-corrupt admission decisions require verification")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("grounding admission identity does not match")
        return self


class GroundingAdmissionService:
    """Apply calibrated abstention without inventing claims or citations."""

    def __init__(self, policy: CalibratedAbstentionPolicy | None = None) -> None:
        self._policy = policy or CalibratedAbstentionPolicy()

    def decide(
        self,
        *,
        claim_set: NormalizedClaimSet,
        citation_set: ClaimCitationSet,
        verification_report: CitationVerificationReport | None,
        request_status: GroundingRequestStatus = GroundingRequestStatus.in_scope,
    ) -> GroundingAdmissionDecision:
        """Admit only policy-qualified direct support or abstain with gaps."""

        if citation_set.source_claim_set_artifact_id != claim_set.artifact_id:
            raise ValueError("citation set does not belong to the supplied claim set")
        if request_status is not GroundingRequestStatus.corrupt_evidence:
            if verification_report is None:
                raise ValueError("a verification report is required")
            if (
                verification_report.source_claim_set_artifact_id
                != claim_set.artifact_id
                or verification_report.claim_citation_set_artifact_id
                != citation_set.artifact_id
            ):
                raise ValueError(
                    "verification report does not belong to supplied inputs"
                )

        if request_status is not GroundingRequestStatus.in_scope:
            code, detail, action = _request_gap(request_status)
            gap = _gap(code, None, detail, action)
            return self._decision(
                claim_set=claim_set,
                citation_set=citation_set,
                report=verification_report,
                request_status=request_status,
                outcome=GroundingAdmissionOutcome.abstained,
                admitted_claims=(),
                admitted_citations=(),
                rejected=(),
                gaps=(gap,),
            )

        assert verification_report is not None
        if not verification_report.claims:
            gap = _gap(
                EvidenceGapCode.no_retrieved_evidence,
                None,
                "No verifiable atomic claim was produced from the closed evidence packet.",
                "Retrieve citation-ready in-scope evidence before answering.",
            )
            return self._decision(
                claim_set=claim_set,
                citation_set=citation_set,
                report=verification_report,
                request_status=request_status,
                outcome=GroundingAdmissionOutcome.abstained,
                admitted_claims=(),
                admitted_citations=(),
                rejected=(),
                gaps=(gap,),
            )

        supported = tuple(
            claim
            for claim in verification_report.claims
            if claim.verdict is EntailmentVerdict.direct_support
        )
        supported_fraction = len(supported) / len(verification_report.claims)
        meets_coverage = (
            len(supported) >= self._policy.minimum_direct_support_claims
            and supported_fraction >= self._policy.minimum_supported_fraction
        )
        unsupported = tuple(
            claim
            for claim in verification_report.claims
            if claim.verdict is not EntailmentVerdict.direct_support
        )
        gaps = tuple(
            _verdict_gap(claim.claim_artifact_id, claim.verdict)
            for claim in unsupported
        )
        rejected = tuple(
            RejectedGroundingClaim(
                claim_artifact_id=claim.claim_artifact_id,
                verdict=claim.verdict,
                evidence_gap_artifact_id=gap.artifact_id,
            )
            for claim, gap in zip(unsupported, gaps, strict=True)
        )
        if not meets_coverage or (
            unsupported and not self._policy.allow_partial_answers
        ):
            coverage_gap = _gap(
                EvidenceGapCode.support_coverage_below_policy,
                None,
                "Verified direct support does not meet the configured answer-admission threshold.",
                "Retrieve or verify enough direct supporting evidence before answering.",
            )
            return self._decision(
                claim_set=claim_set,
                citation_set=citation_set,
                report=verification_report,
                request_status=request_status,
                outcome=GroundingAdmissionOutcome.abstained,
                admitted_claims=(),
                admitted_citations=(),
                rejected=rejected,
                gaps=(*gaps, coverage_gap),
            )

        admitted_claim_ids = tuple(claim.claim_artifact_id for claim in supported)
        admitted_claim_set = set(admitted_claim_ids)
        admitted_citation_ids = tuple(
            link.artifact_id
            for link in citation_set.links
            if link.claim_artifact_id in admitted_claim_set
        )
        outcome = (
            GroundingAdmissionOutcome.partially_admitted
            if unsupported
            else GroundingAdmissionOutcome.admitted
        )
        return self._decision(
            claim_set=claim_set,
            citation_set=citation_set,
            report=verification_report,
            request_status=request_status,
            outcome=outcome,
            admitted_claims=admitted_claim_ids,
            admitted_citations=admitted_citation_ids,
            rejected=rejected,
            gaps=gaps,
        )

    def _decision(
        self,
        *,
        claim_set: NormalizedClaimSet,
        citation_set: ClaimCitationSet,
        report: CitationVerificationReport | None,
        request_status: GroundingRequestStatus,
        outcome: GroundingAdmissionOutcome,
        admitted_claims: tuple[str, ...],
        admitted_citations: tuple[str, ...],
        rejected: tuple[RejectedGroundingClaim, ...],
        gaps: tuple[EvidenceGap, ...],
    ) -> GroundingAdmissionDecision:
        payload = {
            "schema_version": "bijux.canon.reason.grounding_admission_decision.v1",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
            "verification_report_artifact_id": (
                None if report is None else report.artifact_id
            ),
            "policy_artifact_id": self._policy.artifact_id,
            "request_status": request_status.value,
            "outcome": outcome.value,
            "admitted_claim_artifact_ids": admitted_claims,
            "admitted_citation_link_artifact_ids": admitted_citations,
            "rejected_claims": tuple(item.model_dump(mode="json") for item in rejected),
            "evidence_gaps": tuple(item.model_dump(mode="json") for item in gaps),
        }
        return GroundingAdmissionDecision(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=claim_set.artifact_id,
            claim_citation_set_artifact_id=citation_set.artifact_id,
            verification_report_artifact_id=(
                None if report is None else report.artifact_id
            ),
            policy_artifact_id=self._policy.artifact_id,
            request_status=request_status,
            outcome=outcome,
            admitted_claim_artifact_ids=admitted_claims,
            admitted_citation_link_artifact_ids=admitted_citations,
            rejected_claims=rejected,
            evidence_gaps=gaps,
        )


def _gap(
    code: EvidenceGapCode,
    claim_artifact_id: str | None,
    detail: str,
    action: str,
) -> EvidenceGap:
    payload = {
        "code": code.value,
        "claim_artifact_id": claim_artifact_id,
        "detail": detail,
        "required_action": action,
    }
    return EvidenceGap(
        artifact_id=content_artifact_id(payload),
        code=code,
        claim_artifact_id=claim_artifact_id,
        detail=detail,
        required_action=action,
    )


def _verdict_gap(claim_id: str, verdict: EntailmentVerdict) -> EvidenceGap:
    code, detail, action = {
        EntailmentVerdict.opposition: (
            EvidenceGapCode.contradicted_by_evidence,
            "The cited evidence opposes this candidate claim.",
            "Resolve the contradiction or remove the claim.",
        ),
        EntailmentVerdict.ambiguity: (
            EvidenceGapCode.ambiguous_evidence,
            "The cited evidence is related but does not directly entail this claim.",
            "Retrieve a direct supporting span or qualify the claim.",
        ),
        EntailmentVerdict.irrelevance: (
            EvidenceGapCode.irrelevant_evidence,
            "The cited evidence is not substantively relevant to this claim.",
            "Retrieve evidence addressing the claim's terms and scope.",
        ),
        EntailmentVerdict.insufficiency: (
            EvidenceGapCode.insufficient_evidence,
            "The cited span is too weak to verify this claim.",
            "Retrieve a sufficiently detailed exact source span.",
        ),
    }[verdict]
    return _gap(code, claim_id, detail, action)


def _request_gap(
    status: GroundingRequestStatus,
) -> tuple[EvidenceGapCode, str, str]:
    return {
        GroundingRequestStatus.fabricated_entity: (
            EvidenceGapCode.fabricated_entity,
            "The requested entity is not established by admitted evidence.",
            "Correct or identify the entity before retrieving evidence.",
        ),
        GroundingRequestStatus.out_of_scope: (
            EvidenceGapCode.out_of_scope,
            "The question falls outside the admitted corpus scope.",
            "Select an in-scope corpus or explicitly expand the research scope.",
        ),
        GroundingRequestStatus.corrupt_evidence: (
            EvidenceGapCode.integrity_failure,
            "Citation integrity failed, so no claim or citation can be admitted.",
            "Re-retrieve and verify immutable source text and locator digests.",
        ),
    }[status]


__all__ = [
    "CalibratedAbstentionPolicy",
    "EvidenceGap",
    "EvidenceGapCode",
    "GroundingAdmissionDecision",
    "GroundingAdmissionOutcome",
    "GroundingAdmissionService",
    "GroundingRequestStatus",
    "RejectedGroundingClaim",
]
