# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Preserve claim scope, uncertainty, source quality, and conflict in answers."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.citation_linking import ClaimCitationSet
from bijux_canon_reason.grounding.citation_presentation import (
    CitationPresentation,
    CitationPresentationService,
)
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


class ClaimPresentationRole(StrEnum):
    """User-facing evidence role retained independently of entailment."""

    finding = "finding"
    method = "method"
    limitation = "limitation"
    counterevidence = "counterevidence"


class AnswerAnnotationKind(StrEnum):
    """Non-factual answer material that must remain explicitly labeled."""

    answer_limitation = "answer_limitation"
    assumption = "assumption"
    interpretation = "interpretation"


class ClaimContextAnnotation(StableModel):
    """Complete scope and qualification annotation for one atomic claim."""

    artifact_id: str
    claim_artifact_id: str
    presentation_role: ClaimPresentationRole = ClaimPresentationRole.finding
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


class CompatibleClaimScopeGroup(StableModel):
    """Claims grouped only when their explicit scope dimensions are identical."""

    artifact_id: str
    claim_artifact_ids: tuple[str, ...]
    population_scope: tuple[str, ...]
    method_scope: tuple[str, ...]
    temporal_scope: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("claim_artifact_ids")
    @classmethod
    def _validate_claim_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("scope groups require distinct claim identities")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("population_scope", "method_scope", "temporal_scope")
    @classmethod
    def _validate_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not item.strip() for item in value):
            raise ValueError("scope group dimensions must be explicit")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("scope group identity does not match")
        return self


class GroundedAnswerAnnotation(StableModel):
    """Labeled product limitation, assumption, or interpretation."""

    artifact_id: str
    kind: AnswerAnnotationKind
    statement: str
    basis_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("basis_artifact_ids")
    @classmethod
    def _validate_basis_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("answer annotations require distinct basis identities")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("statement")
    @classmethod
    def _validate_statement(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("answer annotation statement must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("answer annotation identity does not match")
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

    schema_version: str = "bijux.canon.reason.nuanced_grounding_representation.v2"
    artifact_id: str
    source_claim_set_artifact_id: str
    claim_citation_set_artifact_id: str
    verification_report_artifact_id: str
    citation_presentation_artifact_id: str
    nodes: tuple[ContextualizedClaimNode, ...]
    contexts: tuple[ClaimContextAnnotation, ...]
    scope_groups: tuple[CompatibleClaimScopeGroup, ...]
    conflicts: tuple[ClaimConflictDeclaration, ...]
    annotations: tuple[GroundedAnswerAnnotation, ...]
    user_answer: str

    @field_validator(
        "artifact_id",
        "source_claim_set_artifact_id",
        "claim_citation_set_artifact_id",
        "verification_report_artifact_id",
        "citation_presentation_artifact_id",
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
        grouped = tuple(
            claim_id
            for group in self.scope_groups
            for claim_id in group.claim_artifact_ids
        )
        if len(grouped) != len(set(grouped)) or set(grouped) != known:
            raise ValueError("scope groups must partition every contextualized claim")
        if any(
            not set(conflict.claim_artifact_ids).issubset(known)
            for conflict in self.conflicts
        ):
            raise ValueError("conflict declaration references an unknown claim")
        material_conflict_ids = _material_conflict_claim_ids(self.contexts)
        if material_conflict_ids and not any(
            material_conflict_ids.issubset(conflict.claim_artifact_ids)
            for conflict in self.conflicts
        ):
            raise ValueError("material counterevidence conflict must be declared")
        if any(
            node.statement not in self.user_answer
            for node in self.nodes
            if node.verdict is EntailmentVerdict.direct_support
        ):
            raise ValueError("user answer must retain every supported claim")
        if any(
            node.statement in self.user_answer
            for node in self.nodes
            if node.verdict is not EntailmentVerdict.direct_support
        ):
            raise ValueError("user answer cannot expose unsupported claims")
        supported = {
            node.claim_artifact_id
            for node in self.nodes
            if node.verdict is EntailmentVerdict.direct_support
        }
        if any(
            conflict.summary not in self.user_answer
            for conflict in self.conflicts
            if set(conflict.claim_artifact_ids).issubset(supported)
        ):
            raise ValueError("user answer must retain every conflict summary")
        if any(
            annotation.statement not in self.user_answer
            for annotation in self.annotations
        ):
            raise ValueError("user answer must retain every labeled annotation")
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
        annotations: tuple[GroundedAnswerAnnotation, ...] = (),
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
        material_conflict_ids = _material_conflict_claim_ids(contexts)
        if material_conflict_ids and not any(
            material_conflict_ids.issubset(conflict.claim_artifact_ids)
            for conflict in conflicts
        ):
            raise ValueError("material counterevidence conflict must be declared")

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
        scope_groups = _scope_groups(tuple(ordered_contexts))
        presentation = CitationPresentationService().present(citation_set)
        answer = render_contextualized_answer(
            nodes=tuple(nodes),
            contexts=tuple(ordered_contexts),
            scope_groups=scope_groups,
            conflicts=conflicts,
            annotations=annotations,
            citation_set=citation_set,
            citation_presentation=presentation,
            admitted_claim_artifact_ids=frozenset(
                node.claim_artifact_id
                for node in nodes
                if node.verdict is EntailmentVerdict.direct_support
            ),
        )
        payload = {
            "schema_version": "bijux.canon.reason.nuanced_grounding_representation.v2",
            "source_claim_set_artifact_id": claim_set.artifact_id,
            "claim_citation_set_artifact_id": citation_set.artifact_id,
            "verification_report_artifact_id": verification_report.artifact_id,
            "citation_presentation_artifact_id": presentation.artifact_id,
            "nodes": tuple(node.model_dump(mode="json") for node in nodes),
            "contexts": tuple(
                context.model_dump(mode="json") for context in ordered_contexts
            ),
            "scope_groups": tuple(
                group.model_dump(mode="json") for group in scope_groups
            ),
            "conflicts": tuple(
                conflict.model_dump(mode="json") for conflict in conflicts
            ),
            "annotations": tuple(
                annotation.model_dump(mode="json") for annotation in annotations
            ),
            "user_answer": answer,
        }
        return NuancedGroundingRepresentation(
            artifact_id=content_artifact_id(payload),
            source_claim_set_artifact_id=claim_set.artifact_id,
            claim_citation_set_artifact_id=citation_set.artifact_id,
            verification_report_artifact_id=verification_report.artifact_id,
            citation_presentation_artifact_id=presentation.artifact_id,
            nodes=tuple(nodes),
            contexts=tuple(ordered_contexts),
            scope_groups=scope_groups,
            conflicts=conflicts,
            annotations=annotations,
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
    presentation_role: ClaimPresentationRole = ClaimPresentationRole.finding,
) -> ClaimContextAnnotation:
    """Create a content-addressed complete claim context."""

    payload = {
        "claim_artifact_id": claim_artifact_id,
        "presentation_role": presentation_role.value,
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
        presentation_role=presentation_role,
        population_scope=population_scope,
        method_scope=method_scope,
        temporal_scope=temporal_scope,
        uncertainty=uncertainty,
        limitations=limitations,
        source_quality=source_quality,
        source_quality_basis=source_quality_basis,
    )


def create_answer_annotation(
    *,
    kind: AnswerAnnotationKind,
    statement: str,
    basis_artifact_ids: tuple[str, ...],
) -> GroundedAnswerAnnotation:
    """Create a content-addressed, explicitly non-factual answer annotation."""

    payload = {
        "kind": kind.value,
        "statement": statement,
        "basis_artifact_ids": basis_artifact_ids,
    }
    return GroundedAnswerAnnotation(
        artifact_id=content_artifact_id(payload),
        kind=kind,
        statement=statement,
        basis_artifact_ids=basis_artifact_ids,
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


def render_contextualized_answer(
    *,
    nodes: tuple[ContextualizedClaimNode, ...],
    contexts: tuple[ClaimContextAnnotation, ...],
    scope_groups: tuple[CompatibleClaimScopeGroup, ...],
    conflicts: tuple[ClaimConflictDeclaration, ...],
    annotations: tuple[GroundedAnswerAnnotation, ...],
    citation_set: ClaimCitationSet,
    citation_presentation: CitationPresentation,
    admitted_claim_artifact_ids: frozenset[str],
) -> str:
    """Render admitted content by scope and role with exact citation numbers."""

    if (
        citation_presentation.source_claim_set_artifact_id
        != citation_set.source_claim_set_artifact_id
        or citation_presentation.claim_citation_set_artifact_id
        != citation_set.artifact_id
    ):
        raise ValueError("contextualized citation presentation lineage diverged")
    known_nodes = {node.claim_artifact_id: node for node in nodes}
    if not admitted_claim_artifact_ids.issubset(known_nodes) or any(
        known_nodes[claim_id].verdict is not EntailmentVerdict.direct_support
        for claim_id in admitted_claim_artifact_ids
    ):
        raise ValueError(
            "only directly supported contextualized claims may be rendered"
        )
    admitted_nodes = tuple(
        node for node in nodes if node.claim_artifact_id in admitted_claim_artifact_ids
    )
    context_by_claim = {item.claim_artifact_id: item for item in contexts}
    node_by_claim = {item.claim_artifact_id: item for item in admitted_nodes}
    citation_numbers_by_claim: dict[str, tuple[int, ...]] = {}
    for claim_id in node_by_claim:
        numbers = {
            citation_presentation.number_for(link.citation_evidence_artifact_id)
            for link in citation_set.links
            if link.claim_artifact_id == claim_id
        }
        citation_numbers_by_claim[claim_id] = tuple(sorted(numbers))

    lines: list[str] = (
        []
        if admitted_nodes
        else ["No verified claims are available for contextualized synthesis."]
    )
    section_roles = (
        ("Source-supported findings", {ClaimPresentationRole.finding}),
        ("Source-supported methods", {ClaimPresentationRole.method}),
        ("Cited limitations", {ClaimPresentationRole.limitation}),
        ("Cited counterevidence", {ClaimPresentationRole.counterevidence}),
    )
    for section, roles in section_roles:
        section_lines: list[str] = []
        for group in scope_groups:
            scoped_nodes = tuple(
                node_by_claim[claim_id]
                for claim_id in group.claim_artifact_ids
                if claim_id in node_by_claim
                and context_by_claim[claim_id].presentation_role in roles
            )
            if not scoped_nodes:
                continue
            section_lines.append(
                "Scope: population="
                + " | ".join(group.population_scope)
                + "; method="
                + " | ".join(group.method_scope)
                + "; time="
                + " | ".join(group.temporal_scope)
            )
            for node in scoped_nodes:
                rendered_numbers = ", ".join(
                    str(number)
                    for number in citation_numbers_by_claim[node.claim_artifact_id]
                )
                section_lines.append(f"- {node.statement} [{rendered_numbers}]")
        if section_lines:
            lines.append(section + ":")
            lines.extend(section_lines)

    if admitted_nodes:
        lines.append("Claim scope and quality limits:")
        for node in admitted_nodes:
            context = context_by_claim[node.claim_artifact_id]
            lines.append(
                f"- Claim {node.claim_ordinal}: uncertainty="
                + " | ".join(context.uncertainty)
                + "; limitations="
                + " | ".join(context.limitations)
                + f"; source quality={context.source_quality.value} "
                + f"({context.source_quality_basis})"
            )

    admitted_conflicts = tuple(
        conflict
        for conflict in conflicts
        if set(conflict.claim_artifact_ids).issubset(admitted_claim_artifact_ids)
    )
    if admitted_conflicts:
        lines.append("Unresolved conflicts and ambiguity:")
        for conflict in admitted_conflicts:
            conflict_numbers = sorted(
                {
                    number
                    for claim_id in conflict.claim_artifact_ids
                    for number in citation_numbers_by_claim[claim_id]
                }
            )
            references = ", ".join(str(number) for number in conflict_numbers)
            lines.append(
                f"- {conflict.summary} Scope: {conflict.scope_note} [{references}]"
            )

    label_by_kind = {
        AnswerAnnotationKind.answer_limitation: "Answer limitations",
        AnswerAnnotationKind.assumption: "Assumptions",
        AnswerAnnotationKind.interpretation: "Product interpretation",
    }
    for kind in AnswerAnnotationKind:
        matching_annotations = tuple(item for item in annotations if item.kind is kind)
        if not matching_annotations:
            continue
        lines.append(label_by_kind[kind] + " (not source-supported facts):")
        lines.extend(f"- {item.statement}" for item in matching_annotations)
    return "\n".join(lines)


def _scope_groups(
    contexts: tuple[ClaimContextAnnotation, ...],
) -> tuple[CompatibleClaimScopeGroup, ...]:
    grouped: dict[
        tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]], list[str]
    ] = {}
    for context in contexts:
        key = (
            context.population_scope,
            context.method_scope,
            context.temporal_scope,
        )
        grouped.setdefault(key, []).append(context.claim_artifact_id)
    result = []
    for (population, method, temporal), claim_ids in grouped.items():
        payload = {
            "claim_artifact_ids": tuple(claim_ids),
            "population_scope": population,
            "method_scope": method,
            "temporal_scope": temporal,
        }
        result.append(
            CompatibleClaimScopeGroup(
                artifact_id=content_artifact_id(payload),
                claim_artifact_ids=tuple(claim_ids),
                population_scope=population,
                method_scope=method,
                temporal_scope=temporal,
            )
        )
    return tuple(result)


def _material_conflict_claim_ids(
    contexts: tuple[ClaimContextAnnotation, ...],
) -> frozenset[str]:
    findings = {
        context.claim_artifact_id
        for context in contexts
        if context.presentation_role is ClaimPresentationRole.finding
    }
    counterevidence = {
        context.claim_artifact_id
        for context in contexts
        if context.presentation_role is ClaimPresentationRole.counterevidence
    }
    return (
        frozenset(findings | counterevidence)
        if findings and counterevidence
        else frozenset()
    )


__all__ = [
    "AnswerAnnotationKind",
    "ClaimConflictDeclaration",
    "ClaimContextAnnotation",
    "ClaimPresentationRole",
    "CompatibleClaimScopeGroup",
    "ConflictRelationship",
    "ContextualizedClaimNode",
    "GroundedAnswerAnnotation",
    "GroundingContextService",
    "NuancedGroundingRepresentation",
    "SourceQualityGrade",
    "create_answer_annotation",
    "create_claim_conflict",
    "create_claim_context",
    "render_contextualized_answer",
]
