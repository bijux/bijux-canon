# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Preserve claim scope, uncertainty, source quality, and conflict in answers."""

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


class SourceQualityGrade(StrEnum):
    """Explicit coarse source-quality assessment, never inferred from presence."""

    high = "high"
    moderate = "moderate"
    limited = "limited"
    unknown = "unknown"


class ConflictRelationship(StrEnum):
    """Declared relation among source-scoped claims."""

    contradictory = "contradictory"
    divergent = "divergent"


class ClaimContextAnnotation(StableModel):
    """Complete scope and qualification annotation for one atomic claim."""

    artifact_id: str
    claim_artifact_id: str
    population_scope: tuple[str, ...]
    method_scope: tuple[str, ...]
    temporal_scope: tuple[str, ...]
    uncertainty: tuple[str, ...]
    limitations: tuple[str, ...]
    source_quality: SourceQualityGrade
    source_quality_basis: str

    @field_validator("artifact_id", "claim_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "population_scope",
        "method_scope",
        "temporal_scope",
        "uncertainty",
        "limitations",
    )
    @classmethod
    def _validate_context_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item.strip() for item in value):
            raise ValueError("claim context dimensions must be explicit and non-empty")
        return value

    @field_validator("source_quality_basis")
    @classmethod
    def _validate_quality_basis(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source quality requires an explicit basis")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("claim context identity does not match")
        return self


class ClaimConflictDeclaration(StableModel):
    """Explicit non-collapsing relationship among two or more claims."""

    artifact_id: str
    relationship: ConflictRelationship
    claim_artifact_ids: tuple[str, ...]
    summary: str
    scope_note: str

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_ids")
    @classmethod
    def _validate_claim_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) < 2 or len(value) != len(set(value)):
            raise ValueError(
                "conflict declarations require distinct participating claims"
            )
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("summary", "scope_note")
    @classmethod
    def _validate_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conflict summary and scope note must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("claim conflict identity does not match")
        return self


class ContextualizedClaimNode(StableModel):
    """One claim-graph node retaining verification, citations, and context."""

    artifact_id: str
    claim_artifact_id: str
    claim_ordinal: int
    statement: str
    verdict: EntailmentVerdict
    citation_link_artifact_ids: tuple[str, ...]
    context_artifact_id: str

    @field_validator("artifact_id", "claim_artifact_id", "context_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("citation_link_artifact_ids")
    @classmethod
    def _validate_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("contextualized claims require exact citation links")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("statement")
    @classmethod
    def _validate_statement(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("contextualized claim statement must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_node(self) -> Self:
        if self.claim_ordinal <= 0:
            raise ValueError("contextualized claim ordinal must be positive")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("contextualized claim identity does not match")
        return self


class NuancedGroundingRepresentation(StableModel):
    """Context-preserving claim graph and deterministic user-facing answer."""

    schema_version: str = "bijux.canon.reason.nuanced_grounding_representation.v1"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    verification_report_artifact_id: str
    nodes: tuple[ContextualizedClaimNode, ...]
    contexts: tuple[ClaimContextAnnotation, ...]
    conflicts: tuple[ClaimConflictDeclaration, ...]
    user_answer: str

    @field_validator(
        "artifact_id",
        "source_claim_set_artifact_id",
        "claim_citation_set_artifact_id",
        "verification_report_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("user_answer")
    @classmethod
    def _validate_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("nuanced grounding answer must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_representation(self) -> Self:
        node_ids = tuple(node.claim_artifact_id for node in self.nodes)
        context_ids = tuple(context.claim_artifact_id for context in self.contexts)
        if node_ids != context_ids:
            raise ValueError("every graph claim requires exactly one ordered context")
        if tuple(node.claim_ordinal for node in self.nodes) != tuple(
            range(1, len(self.nodes) + 1)
        ):
            raise ValueError("contextualized claim ordinals must be contiguous")
        known = set(node_ids)
        if any(
            not set(conflict.claim_artifact_ids).issubset(known)
            for conflict in self.conflicts
        ):
            raise ValueError("conflict declaration references an unknown claim")
        if any(
            context.artifact_id not in self.user_answer for context in self.contexts
        ):
            raise ValueError("user answer must retain every claim context identity")
        if any(conflict.summary not in self.user_answer for conflict in self.conflicts):
            raise ValueError("user answer must retain every conflict summary")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("nuanced grounding identity does not match")
        return self


class GroundingContextService:
    """Build a claim graph and answer without collapsing scope or conflict."""

    def represent(
        self,
        *,
        claim_set: NormalizedClaimSet,
        citation_set: ClaimCitationSet,
        verification_report: CitationVerificationReport,
        contexts: tuple[ClaimContextAnnotation, ...],
        conflicts: tuple[ClaimConflictDeclaration, ...] = (),
    ) -> NuancedGroundingRepresentation:
        """Require complete explicit context and render it deterministically."""

        if (
            citation_set.source_claim_set_artifact_id != claim_set.artifact_id
            or verification_report.source_claim_set_artifact_id != claim_set.artifact_id
            or verification_report.claim_citation_set_artifact_id
            != citation_set.artifact_id
        ):
            raise ValueError("grounding context inputs do not share one claim lineage")
        context_by_claim = {context.claim_artifact_id: context for context in contexts}
        if len(context_by_claim) != len(contexts):
            raise ValueError(
                "claim context annotations contain duplicate claim identities"
            )
        claim_ids = tuple(claim.artifact_id for claim in claim_set.claims)
        if set(context_by_claim) != set(claim_ids):
            raise ValueError("every claim requires one complete context annotation")
        verified_by_claim = {
            claim.claim_artifact_id: claim for claim in verification_report.claims
        }
        links_by_claim = {
            claim_id: tuple(
                link.artifact_id
                for link in citation_set.links
                if link.claim_artifact_id == claim_id
            )
            for claim_id in claim_ids
        }
        known = set(claim_ids)
        if any(
            not set(conflict.claim_artifact_ids).issubset(known)
            for conflict in conflicts
        ):
            raise ValueError("conflict declaration references an unknown claim")

        nodes = []
        ordered_contexts = []
        for claim in claim_set.claims:
            context = context_by_claim[claim.artifact_id]
            verified = verified_by_claim[claim.artifact_id]
            payload = {
                "claim_artifact_id": claim.artifact_id,
                "claim_ordinal": claim.ordinal,
                "statement": claim.statement,
                "verdict": verified.verdict.value,
                "citation_link_artifact_ids": links_by_claim[claim.artifact_id],
                "context_artifact_id": context.artifact_id,
            }
            nodes.append(
                ContextualizedClaimNode(
                    artifact_id=content_artifact_id(payload),
                    claim_artifact_id=claim.artifact_id,
                    claim_ordinal=claim.ordinal,
                    statement=claim.statement,
                    verdict=verified.verdict,
                    citation_link_artifact_ids=links_by_claim[claim.artifact_id],
                    context_artifact_id=context.artifact_id,
                )
            )
            ordered_contexts.append(context)
        answer = _render_answer(tuple(nodes), tuple(ordered_contexts), conflicts)
        payload = {
            "schema_version": "bijux.canon.reason.nuanced_grounding_representation.v1",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
            "verification_report_artifact_id": verification_report.artifact_id,
            "nodes": tuple(node.model_dump(mode="json") for node in nodes),
            "contexts": tuple(
                context.model_dump(mode="json") for context in ordered_contexts
            ),
            "conflicts": tuple(
                conflict.model_dump(mode="json") for conflict in conflicts
            ),
            "user_answer": answer,
        }
        return NuancedGroundingRepresentation(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=claim_set.artifact_id,
            claim_citation_set_artifact_id=citation_set.artifact_id,
            verification_report_artifact_id=verification_report.artifact_id,
            nodes=tuple(nodes),
            contexts=tuple(ordered_contexts),
            conflicts=conflicts,
            user_answer=answer,
        )


def create_claim_context(
    *,
    claim_artifact_id: str,
    population_scope: tuple[str, ...],
    method_scope: tuple[str, ...],
    temporal_scope: tuple[str, ...],
    uncertainty: tuple[str, ...],
    limitations: tuple[str, ...],
    source_quality: SourceQualityGrade,
    source_quality_basis: str,
) -> ClaimContextAnnotation:
    """Create a content-addressed complete claim context."""

    payload = {
        "claim_artifact_id": claim_artifact_id,
        "population_scope": population_scope,
        "method_scope": method_scope,
        "temporal_scope": temporal_scope,
        "uncertainty": uncertainty,
        "limitations": limitations,
        "source_quality": source_quality.value,
        "source_quality_basis": source_quality_basis,
    }
    return ClaimContextAnnotation(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=claim_artifact_id,
        population_scope=population_scope,
        method_scope=method_scope,
        temporal_scope=temporal_scope,
        uncertainty=uncertainty,
        limitations=limitations,
        source_quality=source_quality,
        source_quality_basis=source_quality_basis,
    )


def create_claim_conflict(
    *,
    relationship: ConflictRelationship,
    claim_artifact_ids: tuple[str, ...],
    summary: str,
    scope_note: str,
) -> ClaimConflictDeclaration:
    """Create a content-addressed conflict declaration."""

    payload = {
        "relationship": relationship.value,
        "claim_artifact_ids": claim_artifact_ids,
        "summary": summary,
        "scope_note": scope_note,
    }
    return ClaimConflictDeclaration(
        artifact_id=content_artifact_id(payload),
        relationship=relationship,
        claim_artifact_ids=claim_artifact_ids,
        summary=summary,
        scope_note=scope_note,
    )


def _render_answer(
    nodes: tuple[ContextualizedClaimNode, ...],
    contexts: tuple[ClaimContextAnnotation, ...],
    conflicts: tuple[ClaimConflictDeclaration, ...],
) -> str:
    if not nodes:
        return "No verified claims are available for contextualized synthesis."
    lines = ["Contextualized claims:"]
    for node, context in zip(nodes, contexts, strict=True):
        citations = ", ".join(node.citation_link_artifact_ids)
        lines.append(
            f"- Claim {node.claim_ordinal}: {node.statement} "
            f"[verdict={node.verdict.value}; population={' | '.join(context.population_scope)}; "
            f"method={' | '.join(context.method_scope)}; time={' | '.join(context.temporal_scope)}; "
            f"uncertainty={' | '.join(context.uncertainty)}; "
            f"source_quality={context.source_quality.value} ({context.source_quality_basis}); "
            f"limitations={' | '.join(context.limitations)}; context={context.artifact_id}; "
            f"citations={citations}]"
        )
    if conflicts:
        lines.append("Conflicts and divergence:")
        ordinal_by_id = {node.claim_artifact_id: node.claim_ordinal for node in nodes}
        for conflict in conflicts:
            ordinals = ", ".join(
                str(ordinal_by_id[claim_id]) for claim_id in conflict.claim_artifact_ids
            )
            lines.append(
                f"- {conflict.relationship.value} claims {ordinals}: "
                f"{conflict.summary} Scope: {conflict.scope_note}"
            )
    return "\n".join(lines)


__all__ = [
    "ClaimConflictDeclaration",
    "ClaimContextAnnotation",
    "ConflictRelationship",
    "ContextualizedClaimNode",
    "GroundingContextService",
    "NuancedGroundingRepresentation",
    "SourceQualityGrade",
    "create_claim_conflict",
    "create_claim_context",
]
