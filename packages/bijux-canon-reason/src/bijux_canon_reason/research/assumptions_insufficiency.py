# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Materialize assumptions and evidence deficiencies as research graph nodes."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.abstention import EvidenceGap, EvidenceGapCode
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.evidence_relations import (
    EvidenceRelationAttachment,
    EvidenceRelationKind,
)


class AssumptionStatus(StrEnum):
    """Testing status exposed by the public reason v2 contract."""

    declared = "declared"
    tested = "tested"
    rejected = "rejected"


class AssumptionImpact(StrEnum):
    """Potential answer impact if an assumption fails."""

    low = "low"
    medium = "medium"
    high = "high"


class InsufficiencyOutcome(StrEnum):
    """Whether a claim meets its configured direct-support threshold."""

    sufficient = "sufficient"
    insufficient = "insufficient"


class ResearchDeficiencyKind(StrEnum):
    """Stable actionable gap classes retained in the graph."""

    unstated_premise = "unstated_premise"
    missing_data = "missing_data"
    scope_mismatch = "scope_mismatch"
    weak_evidence = "weak_evidence"
    source_dependence = "source_dependence"
    unanswerable = "unanswerable"


class ResearchDeficiencyStatus(StrEnum):
    """Lifecycle state for an actionable research deficiency."""

    open = "open"
    searching = "searching"
    resolved = "resolved"
    unresolved = "unresolved"


class AssumptionCandidate(StableModel):
    """A premise surfaced by a user, provider, or deterministic rule."""

    artifact_id: str
    claim_artifact_id: str
    statement: str
    impact: AssumptionImpact
    provenance_artifact_id: str | None

    @field_validator("artifact_id", "claim_artifact_id", "provenance_artifact_id")
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator("statement")
    @classmethod
    def _validate_statement(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("assumption statements must not be empty")
        return normalized

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("assumption candidate identity does not match")
        return self


class GraphAssumption(StableModel):
    """Public v2 assumption node attached to one atomic claim."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    artifact_type: Literal["bijux.canon.reason.assumption"] = (
        "bijux.canon.reason.assumption"
    )
    artifact_id: str
    claim_artifact_id: str
    statement: str
    status: AssumptionStatus
    impact: AssumptionImpact

    @field_validator("artifact_id", "claim_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if not self.statement:
            raise ValueError("graph assumptions require a statement")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("graph assumption identity does not match")
        return self


class GraphInsufficiency(StableModel):
    """Public v2 support-coverage assessment for one claim or empty answer."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    artifact_type: Literal["bijux.canon.reason.insufficiency"] = (
        "bijux.canon.reason.insufficiency"
    )
    artifact_id: str
    claim_artifact_ids: tuple[str, ...]
    outcome: InsufficiencyOutcome
    minimum_supports: int
    observed_supports: int
    missing_information: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_ids")
    @classmethod
    def _validate_claim_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("insufficiency claim identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_assessment(self) -> Self:
        if self.minimum_supports <= 0 or self.observed_supports < 0:
            raise ValueError("insufficiency support counts are invalid")
        if self.outcome is InsufficiencyOutcome.sufficient:
            if (
                not self.claim_artifact_ids
                or self.observed_supports < self.minimum_supports
                or self.missing_information
            ):
                raise ValueError("sufficient outcomes require complete claim support")
        elif self.observed_supports >= self.minimum_supports:
            raise ValueError(
                "insufficient outcomes must be below the support threshold"
            )
        if tuple(sorted(set(self.missing_information))) != self.missing_information:
            raise ValueError("missing information must be unique and sorted")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("graph insufficiency identity does not match")
        return self


class ClaimSourceCoverage(StableModel):
    """Exact admitted source identities observed for one claim."""

    claim_artifact_id: str
    source_artifact_ids: tuple[str, ...]

    @field_validator("claim_artifact_id")
    @classmethod
    def _validate_claim_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("source_artifact_ids")
    @classmethod
    def _validate_sources(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("source coverage identities must be unique")
        return tuple(sorted(require_artifact_id(item) for item in value))


class ResearchDeficiency(StableModel):
    """Actionable first-class graph node for a remaining research gap."""

    schema_version: Literal["bijux.canon.reason.research_deficiency.v1"] = (
        "bijux.canon.reason.research_deficiency.v1"
    )
    artifact_type: Literal["bijux.canon.reason.research_deficiency"] = (
        "bijux.canon.reason.research_deficiency"
    )
    artifact_id: str
    graph_artifact_id: str
    target_claim_artifact_id: str | None
    kind: ResearchDeficiencyKind
    description: str
    required_action: str
    source_gap_artifact_id: str | None
    status: ResearchDeficiencyStatus
    priority: int

    @field_validator(
        "artifact_id",
        "graph_artifact_id",
        "target_claim_artifact_id",
        "source_gap_artifact_id",
    )
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_deficiency(self) -> Self:
        if not self.description.strip() or not self.required_action.strip():
            raise ValueError("research deficiencies require detail and an action")
        if not 1 <= self.priority <= 100:
            raise ValueError("research deficiency priority must be within 1..100")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("research deficiency identity does not match")
        return self


class AssumptionInsufficiencyDelta(StableModel):
    """Complete graph delta for assumptions, adequacy, and open deficiencies."""

    schema_version: Literal["bijux.canon.reason.assumption_insufficiency_delta.v1"] = (
        "bijux.canon.reason.assumption_insufficiency_delta.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    relation_attachment_artifact_id: str
    assumptions: tuple[GraphAssumption, ...]
    insufficiencies: tuple[GraphInsufficiency, ...]
    deficiencies: tuple[ResearchDeficiency, ...]

    @field_validator(
        "artifact_id", "graph_artifact_id", "relation_attachment_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_delta(self) -> Self:
        groups = (self.assumptions, self.insufficiencies, self.deficiencies)
        for group in groups:
            ids = tuple(item.artifact_id for item in group)
            if len(ids) != len(set(ids)):
                raise ValueError("graph delta node identities must be unique")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError(
                "assumption and insufficiency delta identity does not match"
            )
        return self


class AssumptionInsufficiencyService:
    """Materialize support thresholds, premises, and every known evidence gap."""

    def assess(
        self,
        *,
        graph_artifact_id: str,
        claim_artifact_ids: tuple[str, ...],
        relation_attachment: EvidenceRelationAttachment,
        minimum_supports: int,
        minimum_independent_sources: int = 2,
        assumptions: tuple[AssumptionCandidate, ...] = (),
        evidence_gaps: tuple[EvidenceGap, ...] = (),
        source_coverage: tuple[ClaimSourceCoverage, ...] = (),
        scope_mismatch: str | None = None,
        unanswerable: str | None = None,
    ) -> AssumptionInsufficiencyDelta:
        """Create closed public nodes and actionable graph deficiencies."""

        require_artifact_id(graph_artifact_id)
        if relation_attachment.graph_artifact_id != graph_artifact_id:
            raise ValueError("relation attachment belongs to another graph")
        if minimum_supports <= 0 or minimum_independent_sources <= 0:
            raise ValueError(
                "support and independent-source thresholds must be positive"
            )
        if len(claim_artifact_ids) != len(set(claim_artifact_ids)):
            raise ValueError("claim identities must be unique")
        for claim_id in claim_artifact_ids:
            require_artifact_id(claim_id)
        known = set(claim_artifact_ids)
        if any(
            item.claim_artifact_id not in known
            for item in relation_attachment.relations
        ):
            raise ValueError("evidence relation references an unknown claim")
        if any(item.claim_artifact_id not in known for item in assumptions):
            raise ValueError("assumption references an unknown claim")
        if any(item.claim_artifact_id not in known for item in source_coverage):
            raise ValueError("source coverage references an unknown claim")
        coverage_claims = tuple(item.claim_artifact_id for item in source_coverage)
        if len(coverage_claims) != len(set(coverage_claims)):
            raise ValueError("source coverage claims must be unique")
        if any(
            item.claim_artifact_id not in known
            for item in evidence_gaps
            if item.claim_artifact_id is not None
        ):
            raise ValueError("evidence gap references an unknown claim")

        graph_assumptions = tuple(_assumption(item) for item in assumptions)
        deficiencies = [
            _deficiency(
                graph_artifact_id,
                candidate.claim_artifact_id,
                ResearchDeficiencyKind.unstated_premise,
                candidate.statement,
                "Test or reject the materialized premise before relying on the claim.",
                candidate.artifact_id,
                80 if candidate.impact is AssumptionImpact.high else 60,
            )
            for candidate in assumptions
        ]
        support_by_claim = {
            claim_id: {
                relation.evidence_artifact_id
                for relation in relation_attachment.relations
                if relation.claim_artifact_id == claim_id
                and relation.relation is EvidenceRelationKind.supports
            }
            for claim_id in claim_artifact_ids
        }
        insufficiencies = []
        for claim_id in claim_artifact_ids:
            observed = len(support_by_claim[claim_id])
            missing: tuple[str, ...] = ()
            if observed < minimum_supports:
                missing = (
                    f"{minimum_supports - observed} additional direct support relation(s)",
                )
                deficiencies.append(
                    _deficiency(
                        graph_artifact_id,
                        claim_id,
                        ResearchDeficiencyKind.weak_evidence,
                        "Direct support is below the configured claim threshold.",
                        "Retrieve and verify additional direct supporting evidence.",
                        None,
                        90,
                    )
                )
            insufficiencies.append(
                _insufficiency(claim_id, minimum_supports, observed, missing)
            )

        for coverage in source_coverage:
            if (
                support_by_claim[coverage.claim_artifact_id]
                and len(coverage.source_artifact_ids) < minimum_independent_sources
            ):
                deficiencies.append(
                    _deficiency(
                        graph_artifact_id,
                        coverage.claim_artifact_id,
                        ResearchDeficiencyKind.source_dependence,
                        "The claim depends on fewer independent sources than required.",
                        "Search for independent source evidence before increasing confidence.",
                        None,
                        85,
                    )
                )
        for gap in evidence_gaps:
            kind = _gap_kind(gap.code)
            deficiencies.append(
                _deficiency(
                    graph_artifact_id,
                    gap.claim_artifact_id,
                    kind,
                    gap.detail,
                    gap.required_action,
                    gap.artifact_id,
                    95 if kind is ResearchDeficiencyKind.scope_mismatch else 80,
                )
            )
        if scope_mismatch:
            deficiencies.append(
                _deficiency(
                    graph_artifact_id,
                    None,
                    ResearchDeficiencyKind.scope_mismatch,
                    scope_mismatch,
                    "Revise the declared scope or keep the request abstained.",
                    None,
                    100,
                )
            )
        if unanswerable:
            deficiencies.append(
                _deficiency(
                    graph_artifact_id,
                    None,
                    ResearchDeficiencyKind.unanswerable,
                    unanswerable,
                    "Reformulate the question or record explicit insufficiency.",
                    None,
                    100,
                )
            )
        ordered_deficiencies = tuple(
            sorted(
                {item.artifact_id: item for item in deficiencies}.values(),
                key=lambda item: (-item.priority, item.artifact_id),
            )
        )
        payload = {
            "schema_version": "bijux.canon.reason.assumption_insufficiency_delta.v1",
            "graph_artifact_id": graph_artifact_id,
            "relation_attachment_artifact_id": relation_attachment.artifact_id,
            "assumptions": tuple(
                item.model_dump(mode="json") for item in graph_assumptions
            ),
            "insufficiencies": tuple(
                item.model_dump(mode="json") for item in insufficiencies
            ),
            "deficiencies": tuple(
                item.model_dump(mode="json") for item in ordered_deficiencies
            ),
        }
        return AssumptionInsufficiencyDelta(
            artifact_id=content_artifact_id(payload),
            graph_artifact_id=graph_artifact_id,
            relation_attachment_artifact_id=relation_attachment.artifact_id,
            assumptions=graph_assumptions,
            insufficiencies=tuple(insufficiencies),
            deficiencies=ordered_deficiencies,
        )


def create_assumption_candidate(
    *,
    claim_artifact_id: str,
    statement: str,
    impact: AssumptionImpact,
    provenance_artifact_id: str | None = None,
) -> AssumptionCandidate:
    """Create one immutable materialized premise candidate."""

    normalized = " ".join(statement.split())
    payload = {
        "claim_artifact_id": claim_artifact_id,
        "statement": normalized,
        "impact": impact.value,
        "provenance_artifact_id": provenance_artifact_id,
    }
    return AssumptionCandidate(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=claim_artifact_id,
        statement=normalized,
        impact=impact,
        provenance_artifact_id=provenance_artifact_id,
    )


def _assumption(candidate: AssumptionCandidate) -> GraphAssumption:
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.assumption",
        "claim_artifact_id": candidate.claim_artifact_id,
        "statement": candidate.statement,
        "status": AssumptionStatus.declared.value,
        "impact": candidate.impact.value,
    }
    return GraphAssumption(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=candidate.claim_artifact_id,
        statement=candidate.statement,
        status=AssumptionStatus.declared,
        impact=candidate.impact,
    )


def _insufficiency(
    claim_id: str, minimum: int, observed: int, missing: tuple[str, ...]
) -> GraphInsufficiency:
    outcome = (
        InsufficiencyOutcome.sufficient
        if observed >= minimum
        else InsufficiencyOutcome.insufficient
    )
    ordered_missing = tuple(sorted(set(missing)))
    payload = {
        "schema_version": "2.0.0",
        "artifact_type": "bijux.canon.reason.insufficiency",
        "claim_artifact_ids": (claim_id,),
        "outcome": outcome.value,
        "minimum_supports": minimum,
        "observed_supports": observed,
        "missing_information": ordered_missing,
    }
    return GraphInsufficiency(
        artifact_id=content_artifact_id(payload),
        claim_artifact_ids=(claim_id,),
        outcome=outcome,
        minimum_supports=minimum,
        observed_supports=observed,
        missing_information=ordered_missing,
    )


def _deficiency(
    graph_id: str,
    claim_id: str | None,
    kind: ResearchDeficiencyKind,
    description: str,
    action: str,
    source_gap_id: str | None,
    priority: int,
) -> ResearchDeficiency:
    normalized_description = " ".join(description.split())
    normalized_action = " ".join(action.split())
    payload = {
        "schema_version": "bijux.canon.reason.research_deficiency.v1",
        "artifact_type": "bijux.canon.reason.research_deficiency",
        "graph_artifact_id": graph_id,
        "target_claim_artifact_id": claim_id,
        "kind": kind.value,
        "description": normalized_description,
        "required_action": normalized_action,
        "source_gap_artifact_id": source_gap_id,
        "status": ResearchDeficiencyStatus.open.value,
        "priority": priority,
    }
    return ResearchDeficiency(
        artifact_id=content_artifact_id(payload),
        graph_artifact_id=graph_id,
        target_claim_artifact_id=claim_id,
        kind=kind,
        description=normalized_description,
        required_action=normalized_action,
        source_gap_artifact_id=source_gap_id,
        status=ResearchDeficiencyStatus.open,
        priority=priority,
    )


def _gap_kind(code: EvidenceGapCode) -> ResearchDeficiencyKind:
    return {
        EvidenceGapCode.fabricated_entity: ResearchDeficiencyKind.unanswerable,
        EvidenceGapCode.out_of_scope: ResearchDeficiencyKind.scope_mismatch,
        EvidenceGapCode.integrity_failure: ResearchDeficiencyKind.weak_evidence,
        EvidenceGapCode.no_retrieved_evidence: ResearchDeficiencyKind.missing_data,
        EvidenceGapCode.contradicted_by_evidence: ResearchDeficiencyKind.weak_evidence,
        EvidenceGapCode.ambiguous_evidence: ResearchDeficiencyKind.weak_evidence,
        EvidenceGapCode.irrelevant_evidence: ResearchDeficiencyKind.weak_evidence,
        EvidenceGapCode.insufficient_evidence: ResearchDeficiencyKind.weak_evidence,
        EvidenceGapCode.support_coverage_below_policy: ResearchDeficiencyKind.weak_evidence,
    }[code]


__all__ = [
    "AssumptionCandidate",
    "AssumptionImpact",
    "AssumptionInsufficiencyDelta",
    "AssumptionInsufficiencyService",
    "AssumptionStatus",
    "ClaimSourceCoverage",
    "GraphAssumption",
    "GraphInsufficiency",
    "InsufficiencyOutcome",
    "ResearchDeficiency",
    "ResearchDeficiencyKind",
    "ResearchDeficiencyStatus",
    "create_assumption_candidate",
]
