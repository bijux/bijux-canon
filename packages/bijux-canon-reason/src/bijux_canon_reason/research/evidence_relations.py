# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Attach verified evidence relationships to research claims without collapse."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_verification import (
    CitationIntegrityStatus,
    CitationVerificationOutcome,
    CitationVerificationReport,
    EntailmentVerdict,
    EvidenceEntailmentAssessment,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class EvidenceRelationKind(StrEnum):
    """Graph relationship admitted by the public reason v2 contract."""

    supports = "supports"
    opposes = "opposes"
    ambiguous = "ambiguous"


class RelationClassificationMode(StrEnum):
    """Authority that determined the graph relation."""

    deterministic_verification = "deterministic_verification"


class RelationRejectionReason(StrEnum):
    """Why verified evidence did not become a claim relation edge."""

    irrelevance = "irrelevance"
    insufficiency = "insufficiency"


class GraphEvidenceRelation(StableModel):
    """Public v2 evidence relation bound to one exact evidence artifact."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    artifact_type: Literal["bijux.canon.reason.evidence_relation"] = (
        "bijux.canon.reason.evidence_relation"
    )
    artifact_id: str
    claim_artifact_id: str
    evidence_artifact_id: str
    relation: EvidenceRelationKind
    strength: float
    rationale: str

    @field_validator("artifact_id", "claim_artifact_id", "evidence_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_relation(self) -> Self:
        if not math.isfinite(self.strength) or not 0.0 <= self.strength <= 1.0:
            raise ValueError("evidence relation strength must be finite and in [0, 1]")
        if not self.rationale:
            raise ValueError("evidence relations require a rationale")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("evidence relation identity does not match its payload")
        return self


class EvidenceRelationTrace(StableModel):
    """Exact verification lineage behind one admitted relation edge."""

    artifact_id: str
    relation_artifact_id: str
    assessment_artifact_id: str
    claim_citation_link_artifact_id: str
    citation_evidence_artifact_id: str
    integrity: CitationIntegrityStatus
    deterministic_policy_artifact_id: str
    verification_report_artifact_id: str
    provider_provenance_artifact_id: str | None
    classification_mode: RelationClassificationMode

    @field_validator(
        "artifact_id",
        "relation_artifact_id",
        "assessment_artifact_id",
        "claim_citation_link_artifact_id",
        "citation_evidence_artifact_id",
        "deterministic_policy_artifact_id",
        "verification_report_artifact_id",
        "provider_provenance_artifact_id",
    )
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_trace(self) -> Self:
        if self.integrity is not CitationIntegrityStatus.verified:
            raise ValueError("graph relations require verified citation integrity")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("evidence relation trace identity does not match")
        return self


class RejectedEvidenceRelation(StableModel):
    """Verified link retained when it cannot become a relation edge."""

    artifact_id: str
    claim_artifact_id: str
    citation_evidence_artifact_id: str
    assessment_artifact_id: str
    reason: RelationRejectionReason
    rationale_code: str

    @field_validator(
        "artifact_id",
        "claim_artifact_id",
        "citation_evidence_artifact_id",
        "assessment_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_rejection(self) -> Self:
        if not self.rationale_code:
            raise ValueError("rejected relations require a rationale code")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("rejected evidence relation identity does not match")
        return self


class EvidenceRelationAttachment(StableModel):
    """Complete non-collapsing relation attachment for one verification report."""

    schema_version: Literal["bijux.canon.reason.evidence_relation_attachment.v1"] = (
        "bijux.canon.reason.evidence_relation_attachment.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    verification_report_artifact_id: str
    relations: tuple[GraphEvidenceRelation, ...]
    traces: tuple[EvidenceRelationTrace, ...]
    rejected: tuple[RejectedEvidenceRelation, ...]

    @field_validator(
        "artifact_id", "graph_artifact_id", "verification_report_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_attachment(self) -> Self:
        if tuple(item.relation_artifact_id for item in self.traces) != tuple(
            item.artifact_id for item in self.relations
        ):
            raise ValueError("every admitted relation requires one ordered trace")
        assessment_ids = tuple(item.assessment_artifact_id for item in self.traces) + (
            tuple(item.assessment_artifact_id for item in self.rejected)
        )
        if len(assessment_ids) != len(set(assessment_ids)):
            raise ValueError("each verification assessment must be classified once")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("evidence relation attachment identity does not match")
        return self


class EvidenceRelationAttachmentService:
    """Map deterministic link verdicts to graph edges and explicit rejections."""

    def attach(
        self,
        *,
        graph_artifact_id: str,
        report: CitationVerificationReport,
        provider_provenance_artifact_id: str | None = None,
    ) -> EvidenceRelationAttachment:
        """Attach every assessment without allowing provider claims to decide edges."""

        require_artifact_id(graph_artifact_id)
        if provider_provenance_artifact_id is not None:
            require_artifact_id(provider_provenance_artifact_id)
        relations: list[GraphEvidenceRelation] = []
        traces: list[EvidenceRelationTrace] = []
        rejected: list[RejectedEvidenceRelation] = []
        for claim in report.claims:
            for assessment in claim.assessments:
                relation_kind = _relation_kind(assessment.verdict)
                if relation_kind is None:
                    rejected.append(_reject(assessment))
                    continue
                relation = _create_relation(assessment, relation_kind)
                relations.append(relation)
                trace_payload = {
                    "relation_artifact_id": relation.artifact_id,
                    "assessment_artifact_id": assessment.artifact_id,
                    "claim_citation_link_artifact_id": assessment.claim_citation_link_artifact_id,
                    "citation_evidence_artifact_id": assessment.citation_evidence_artifact_id,
                    "integrity": assessment.integrity.value,
                    "deterministic_policy_artifact_id": report.policy_artifact_id,
                    "verification_report_artifact_id": report.artifact_id,
                    "provider_provenance_artifact_id": provider_provenance_artifact_id,
                    "classification_mode": RelationClassificationMode.deterministic_verification.value,
                }
                traces.append(
                    EvidenceRelationTrace(
                        artifact_id=content_artifact_id(trace_payload),
                        relation_artifact_id=relation.artifact_id,
                        assessment_artifact_id=assessment.artifact_id,
                        claim_citation_link_artifact_id=assessment.claim_citation_link_artifact_id,
                        citation_evidence_artifact_id=assessment.citation_evidence_artifact_id,
                        integrity=assessment.integrity,
                        deterministic_policy_artifact_id=report.policy_artifact_id,
                        verification_report_artifact_id=report.artifact_id,
                        provider_provenance_artifact_id=provider_provenance_artifact_id,
                        classification_mode=RelationClassificationMode.deterministic_verification,
                    )
                )
        if report.outcome is CitationVerificationOutcome.no_claims and (
            relations or traces or rejected
        ):
            raise ValueError("no-claims reports cannot attach evidence relations")
        payload = {
            "schema_version": "bijux.canon.reason.evidence_relation_attachment.v1",
            "graph_artifact_id": graph_artifact_id,
            "verification_report_artifact_id": report.artifact_id,
            "relations": tuple(item.model_dump(mode="json") for item in relations),
            "traces": tuple(item.model_dump(mode="json") for item in traces),
            "rejected": tuple(item.model_dump(mode="json") for item in rejected),
        }
        return EvidenceRelationAttachment(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_artifact_id,
            verification_report_artifact_id=report.artifact_id,
            relations=tuple(relations),
            traces=tuple(traces),
            rejected=tuple(rejected),
        )


def _relation_kind(verdict: EntailmentVerdict) -> EvidenceRelationKind | None:
    return {
        EntailmentVerdict.direct_support: EvidenceRelationKind.supports,
        EntailmentVerdict.opposition: EvidenceRelationKind.opposes,
        EntailmentVerdict.ambiguity: EvidenceRelationKind.ambiguous,
        EntailmentVerdict.irrelevance: None,
        EntailmentVerdict.insufficiency: None,
    }[verdict]


def _create_relation(
    assessment: EvidenceEntailmentAssessment, kind: EvidenceRelationKind
) -> GraphEvidenceRelation:
    strength = 1.0 if assessment.exact_claim_span else assessment.claim_term_coverage
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.evidence_relation",
        "claim_artifact_id": assessment.claim_artifact_id,
        "evidence_artifact_id": assessment.citation_evidence_artifact_id,
        "relation": kind.value,
        "strength": strength,
        "rationale": assessment.rationale_code,
    }
    return GraphEvidenceRelation(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=assessment.claim_artifact_id,
        evidence_artifact_id=assessment.citation_evidence_artifact_id,
        relation=kind,
        strength=strength,
        rationale=assessment.rationale_code,
    )


def _reject(assessment: EvidenceEntailmentAssessment) -> RejectedEvidenceRelation:
    reason = RelationRejectionReason(assessment.verdict.value)
    payload = {
        "claim_artifact_id": assessment.claim_artifact_id,
        "citation_evidence_artifact_id": assessment.citation_evidence_artifact_id,
        "assessment_artifact_id": assessment.artifact_id,
        "reason": reason.value,
        "rationale_code": assessment.rationale_code,
    }
    return RejectedEvidenceRelation(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=assessment.claim_artifact_id,
        citation_evidence_artifact_id=assessment.citation_evidence_artifact_id,
        assessment_artifact_id=assessment.artifact_id,
        reason=reason,
        rationale_code=assessment.rationale_code,
    )


__all__ = [
    "EvidenceRelationAttachment",
    "EvidenceRelationAttachmentService",
    "EvidenceRelationKind",
    "EvidenceRelationTrace",
    "GraphEvidenceRelation",
    "RejectedEvidenceRelation",
    "RelationClassificationMode",
    "RelationRejectionReason",
]
