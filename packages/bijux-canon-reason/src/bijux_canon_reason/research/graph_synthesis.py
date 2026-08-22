# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Render terminal verified research graph state without inventing claims."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.context_representation import (
    ClaimConflictDeclaration,
    ClaimContextAnnotation,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.assumptions_insufficiency import (
    AssumptionInsufficiencyDelta,
    AssumptionStatus,
    GraphAssumption,
    InsufficiencyOutcome,
    ResearchDeficiency,
    ResearchDeficiencyStatus,
)
from bijux_canon_reason.research.claim_merging import ClaimMergeResult
from bijux_canon_reason.research.convergence import (
    ConvergenceDecision,
    ConvergenceOutcome,
)
from bijux_canon_reason.research.evidence_relations import (
    EvidenceRelationAttachment,
    EvidenceRelationKind,
    GraphEvidenceRelation,
)


class GraphSynthesisErrorCode(StrEnum):
    """Stable reasons verified graph state cannot be synthesized."""

    research_not_terminal = "research_not_terminal"
    research_cancelled = "research_cancelled"
    graph_identity_mismatch = "graph_identity_mismatch"
    relation_attachment_mismatch = "relation_attachment_mismatch"
    unknown_claim = "unknown_claim"
    incomplete_context = "incomplete_context"


class GraphSynthesisError(ValueError):
    """Verified graph state is inconsistent or is not ready for synthesis."""

    def __init__(self, code: GraphSynthesisErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ResearchSynthesisOutcome(StrEnum):
    """Honest answer disposition derived from terminal graph state."""

    answered = "answered"
    partial = "partial"
    insufficient = "insufficient"


class SynthesisConfidenceLevel(StrEnum):
    """Coarse interpretation of the transparent graph-derived score."""

    unsupported = "unsupported"
    low = "low"
    moderate = "moderate"
    high = "high"


class SynthesisClaimSection(StrEnum):
    """Placement of an admitted claim in the rendered answer."""

    consensus = "consensus"
    conflict = "conflict"


class GraphConfidenceBasis(StableModel):
    """Exact inputs to a bounded, non-probabilistic confidence indicator."""

    artifact_id: str
    support_evidence_artifact_ids: tuple[str, ...]
    opposition_evidence_artifact_ids: tuple[str, ...]
    ambiguous_evidence_artifact_ids: tuple[str, ...]
    declared_conflict_artifact_ids: tuple[str, ...]
    material_assumption_artifact_ids: tuple[str, ...]
    open_deficiency_artifact_ids: tuple[str, ...]
    score: float
    level: SynthesisConfidenceLevel
    calculation: Literal[
        "support/(support+opposition+ambiguity+declared_conflicts+material_assumptions+open_deficiencies)"
    ] = "support/(support+opposition+ambiguity+declared_conflicts+material_assumptions+open_deficiencies)"

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "support_evidence_artifact_ids",
        "opposition_evidence_artifact_ids",
        "ambiguous_evidence_artifact_ids",
        "declared_conflict_artifact_ids",
        "material_assumption_artifact_ids",
        "open_deficiency_artifact_ids",
    )
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("confidence inputs must be unique and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_basis(self) -> Self:
        denominator = sum(
            len(items)
            for items in (
                self.support_evidence_artifact_ids,
                self.opposition_evidence_artifact_ids,
                self.ambiguous_evidence_artifact_ids,
                self.declared_conflict_artifact_ids,
                self.material_assumption_artifact_ids,
                self.open_deficiency_artifact_ids,
            )
        )
        expected = (
            0.0
            if denominator == 0
            else round(len(self.support_evidence_artifact_ids) / denominator, 6)
        )
        if self.score != expected or self.level is not _confidence_level(expected):
            raise ValueError(
                "confidence must be derived from its declared graph inputs"
            )
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("confidence basis identity does not match")
        return self


class SynthesizedGraphClaim(StableModel):
    """One supported canonical claim with exact evidence and confidence lineage."""

    artifact_id: str
    canonical_claim_artifact_id: str
    statement: str
    section: SynthesisClaimSection
    evidence_relation_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    confidence: GraphConfidenceBasis

    @field_validator("artifact_id", "canonical_claim_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("evidence_relation_artifact_ids", "evidence_artifact_ids")
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or tuple(sorted(set(value))) != value:
            raise ValueError("synthesized claims require unique sorted evidence")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_claim(self) -> Self:
        if (
            not self.statement.strip()
            or not self.confidence.support_evidence_artifact_ids
        ):
            raise ValueError("synthesis may expose only supported substantive claims")
        expected_section = SynthesisClaimSection.consensus
        if (
            self.confidence.opposition_evidence_artifact_ids
            or self.confidence.declared_conflict_artifact_ids
        ):
            expected_section = SynthesisClaimSection.conflict
        if self.section is not expected_section:
            raise ValueError("claim section must reflect admitted opposition")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("synthesized claim identity does not match")
        return self


class VerifiedGraphConflict(StableModel):
    """Canonicalized conflict retaining its exact graph sources."""

    artifact_id: str
    canonical_claim_artifact_ids: tuple[str, ...]
    statement: str
    source_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("canonical_claim_artifact_ids", "source_artifact_ids")
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or tuple(sorted(set(value))) != value:
            raise ValueError("synthesis conflicts require unique sorted identities")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_conflict(self) -> Self:
        if not self.statement.strip():
            raise ValueError("synthesis conflicts require a statement")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("synthesis conflict identity does not match")
        return self


class GraphSynthesisLimitation(StableModel):
    """A source-bound limitation retained in the answer."""

    artifact_id: str
    statement: str
    canonical_claim_artifact_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("canonical_claim_artifact_ids", "source_artifact_ids")
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if tuple(sorted(set(value))) != value:
            raise ValueError("limitation identities must be unique and sorted")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_limitation(self) -> Self:
        if not self.statement.strip() or not self.source_artifact_ids:
            raise ValueError("limitations require text and exact graph sources")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("synthesis limitation identity does not match")
        return self


class VerifiedGraphSynthesis(StableModel):
    """Content-addressed answer whose complete structure comes from graph state."""

    schema_version: Literal["bijux.canon.reason.verified_graph_synthesis.v1"] = (
        "bijux.canon.reason.verified_graph_synthesis.v1"
    )
    artifact_id: str
    graph_artifact_id: str
    question: str
    claim_merge_artifact_id: str
    evidence_relation_attachment_artifact_id: str
    assumption_insufficiency_artifact_id: str
    convergence_decision_artifact_id: str
    outcome: ResearchSynthesisOutcome
    consensus: tuple[SynthesizedGraphClaim, ...]
    conflicts: tuple[VerifiedGraphConflict, ...]
    conflicted_claims: tuple[SynthesizedGraphClaim, ...]
    limitations: tuple[GraphSynthesisLimitation, ...]
    assumptions: tuple[GraphAssumption, ...]
    remaining_gaps: tuple[ResearchDeficiency, ...]
    answer: str

    @field_validator(
        "artifact_id",
        "graph_artifact_id",
        "claim_merge_artifact_id",
        "evidence_relation_attachment_artifact_id",
        "assumption_insufficiency_artifact_id",
        "convergence_decision_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_synthesis(self) -> Self:
        claim_ids = tuple(
            item.canonical_claim_artifact_id
            for item in self.consensus + self.conflicted_claims
        )
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("a canonical claim may appear in only one answer section")
        if not self.limitations:
            raise ValueError("verified graph synthesis must state limitations")
        required_answer_ids = (
            tuple(item.artifact_id for item in self.consensus)
            + tuple(item.artifact_id for item in self.conflicted_claims)
            + tuple(item.artifact_id for item in self.conflicts)
            + tuple(item.artifact_id for item in self.limitations)
            + tuple(item.artifact_id for item in self.assumptions)
            + tuple(item.artifact_id for item in self.remaining_gaps)
        )
        if any(item not in self.answer for item in required_answer_ids):
            raise ValueError(
                "rendered answer must retain every structured graph identity"
            )
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("verified graph synthesis identity does not match")
        return self


class VerifiedGraphSynthesisService:
    """Join verified terminal graph products into a deterministic answer."""

    def synthesize(
        self,
        *,
        question: str,
        claim_merge: ClaimMergeResult,
        evidence_relations: EvidenceRelationAttachment,
        assumption_insufficiency: AssumptionInsufficiencyDelta,
        convergence: ConvergenceDecision,
        contexts: tuple[ClaimContextAnnotation, ...] = (),
        declared_conflicts: tuple[ClaimConflictDeclaration, ...] = (),
    ) -> VerifiedGraphSynthesis:
        """Synthesize only terminal, mutually consistent, verified graph state."""

        normalized_question = " ".join(question.split())
        if not normalized_question:
            raise ValueError("verified graph synthesis requires a question")
        if not convergence.stop:
            raise GraphSynthesisError(
                GraphSynthesisErrorCode.research_not_terminal,
                "research must reach a terminal convergence decision before synthesis",
            )
        if convergence.outcome is ConvergenceOutcome.cancelled:
            raise GraphSynthesisError(
                GraphSynthesisErrorCode.research_cancelled,
                "cancelled research cannot produce a substantive synthesis",
            )
        graph_id = claim_merge.graph_artifact_id
        if (
            evidence_relations.graph_artifact_id != graph_id
            or assumption_insufficiency.graph_artifact_id != graph_id
            or convergence.current_graph_artifact_id != graph_id
        ):
            raise GraphSynthesisError(
                GraphSynthesisErrorCode.graph_identity_mismatch,
                "all synthesis inputs must describe the same current graph",
            )
        if (
            assumption_insufficiency.relation_attachment_artifact_id
            != evidence_relations.artifact_id
        ):
            raise GraphSynthesisError(
                GraphSynthesisErrorCode.relation_attachment_mismatch,
                "assumption state must derive from the supplied relation attachment",
            )

        canonical_by_id = {
            item.artifact_id: item for item in claim_merge.canonical_claims
        }
        source_to_canonical = {
            item.source_claim_artifact_id: item.canonical_claim_artifact_id
            for item in claim_merge.mappings
        }

        def resolve(claim_id: str) -> str:
            if claim_id in canonical_by_id:
                return claim_id
            try:
                return source_to_canonical[claim_id]
            except KeyError as error:
                raise GraphSynthesisError(
                    GraphSynthesisErrorCode.unknown_claim,
                    f"graph component references unknown claim {claim_id}",
                ) from error

        relations_by_claim: dict[str, list[GraphEvidenceRelation]] = defaultdict(list)
        for relation in evidence_relations.relations:
            relations_by_claim[resolve(relation.claim_artifact_id)].append(relation)

        assumptions_by_claim: dict[str, list[GraphAssumption]] = defaultdict(list)
        for assumption in assumption_insufficiency.assumptions:
            assumptions_by_claim[resolve(assumption.claim_artifact_id)].append(
                assumption
            )

        open_statuses = {
            ResearchDeficiencyStatus.open,
            ResearchDeficiencyStatus.searching,
            ResearchDeficiencyStatus.unresolved,
        }
        remaining_gaps = tuple(
            sorted(
                (
                    item
                    for item in assumption_insufficiency.deficiencies
                    if item.status in open_statuses
                ),
                key=lambda item: (-item.priority, item.artifact_id),
            )
        )
        deficiencies_by_claim: dict[str, list[ResearchDeficiency]] = defaultdict(list)
        global_deficiencies = []
        for deficiency in remaining_gaps:
            if deficiency.target_claim_artifact_id is None:
                global_deficiencies.append(deficiency)
            else:
                deficiencies_by_claim[
                    resolve(deficiency.target_claim_artifact_id)
                ].append(deficiency)

        context_by_claim: dict[str, ClaimContextAnnotation] = {}
        for context in contexts:
            canonical_id = resolve(context.claim_artifact_id)
            if canonical_id in context_by_claim:
                raise GraphSynthesisError(
                    GraphSynthesisErrorCode.incomplete_context,
                    "each canonical claim may have at most one synthesis context",
                )
            context_by_claim[canonical_id] = context

        declared_conflicts_by_claim: dict[str, list[ClaimConflictDeclaration]] = (
            defaultdict(list)
        )
        for conflict in declared_conflicts:
            for canonical_id in {
                resolve(claim_id) for claim_id in conflict.claim_artifact_ids
            }:
                declared_conflicts_by_claim[canonical_id].append(conflict)

        claims = []
        for canonical_id, canonical in sorted(canonical_by_id.items()):
            relations = tuple(relations_by_claim[canonical_id])
            support = _evidence_ids(relations, EvidenceRelationKind.supports)
            if not support:
                continue
            opposition = _evidence_ids(relations, EvidenceRelationKind.opposes)
            ambiguous = _evidence_ids(relations, EvidenceRelationKind.ambiguous)
            declared_conflict_ids = tuple(
                sorted(
                    item.artifact_id
                    for item in declared_conflicts_by_claim[canonical_id]
                )
            )
            material_assumptions = tuple(
                sorted(
                    item.artifact_id
                    for item in assumptions_by_claim[canonical_id]
                    if item.status is not AssumptionStatus.tested
                )
            )
            claim_deficiencies = tuple(
                sorted(
                    item.artifact_id
                    for item in (
                        deficiencies_by_claim[canonical_id] + global_deficiencies
                    )
                )
            )
            confidence = _confidence(
                support,
                opposition,
                ambiguous,
                declared_conflict_ids,
                material_assumptions,
                claim_deficiencies,
            )
            section = (
                SynthesisClaimSection.conflict
                if opposition or declared_conflict_ids
                else SynthesisClaimSection.consensus
            )
            relation_ids = tuple(sorted(item.artifact_id for item in relations))
            evidence_ids = tuple(
                sorted({item.evidence_artifact_id for item in relations})
            )
            claim_payload = {
                "canonical_claim_artifact_id": canonical_id,
                "statement": canonical.preferred_statement,
                "section": section.value,
                "evidence_relation_artifact_ids": relation_ids,
                "evidence_artifact_ids": evidence_ids,
                "confidence": confidence.model_dump(mode="json"),
            }
            claims.append(
                SynthesizedGraphClaim(
                    artifact_id=content_artifact_id(claim_payload),
                    canonical_claim_artifact_id=canonical_id,
                    statement=canonical.preferred_statement,
                    section=section,
                    evidence_relation_artifact_ids=relation_ids,
                    evidence_artifact_ids=evidence_ids,
                    confidence=confidence,
                )
            )

        consensus = tuple(
            item for item in claims if item.section is SynthesisClaimSection.consensus
        )
        conflicted_claims = tuple(
            item for item in claims if item.section is SynthesisClaimSection.conflict
        )
        conflicts = _conflicts(
            conflicted_claims, declared_conflicts, relations_by_claim, resolve
        )
        limitations = _limitations(
            graph_id=graph_id,
            claim_merge_artifact_id=claim_merge.artifact_id,
            contexts=context_by_claim,
            insufficiency=assumption_insufficiency,
            convergence=convergence,
            resolve=resolve,
        )
        assumptions = tuple(
            sorted(
                assumption_insufficiency.assumptions,
                key=lambda item: item.artifact_id,
            )
        )
        outcome = _outcome(
            claims=tuple(claims),
            conflicts=conflicts,
            assumptions=assumptions,
            gaps=remaining_gaps,
            convergence=convergence,
        )
        answer = _render_answer(
            question=normalized_question,
            outcome=outcome,
            consensus=consensus,
            conflicts=conflicts,
            conflicted_claims=conflicted_claims,
            limitations=limitations,
            assumptions=assumptions,
            remaining_gaps=remaining_gaps,
        )
        result_payload: dict[str, object] = {
            "schema_version": "bijux.canon.reason.verified_graph_synthesis.v1",
            "graph_artifact_id": graph_id,
            "question": normalized_question,
            "claim_merge_artifact_id": claim_merge.artifact_id,
            "evidence_relation_attachment_artifact_id": evidence_relations.artifact_id,
            "assumption_insufficiency_artifact_id": assumption_insufficiency.artifact_id,
            "convergence_decision_artifact_id": convergence.artifact_id,
            "outcome": outcome.value,
            "consensus": tuple(item.model_dump(mode="json") for item in consensus),
            "conflicts": tuple(item.model_dump(mode="json") for item in conflicts),
            "conflicted_claims": tuple(
                item.model_dump(mode="json") for item in conflicted_claims
            ),
            "limitations": tuple(item.model_dump(mode="json") for item in limitations),
            "assumptions": tuple(item.model_dump(mode="json") for item in assumptions),
            "remaining_gaps": tuple(
                item.model_dump(mode="json") for item in remaining_gaps
            ),
            "answer": answer,
        }
        return VerifiedGraphSynthesis(
            artifact_id=content_artifact_id(result_payload),
            graph_artifact_id=graph_id,
            question=normalized_question,
            claim_merge_artifact_id=claim_merge.artifact_id,
            evidence_relation_attachment_artifact_id=evidence_relations.artifact_id,
            assumption_insufficiency_artifact_id=assumption_insufficiency.artifact_id,
            convergence_decision_artifact_id=convergence.artifact_id,
            outcome=outcome,
            consensus=consensus,
            conflicts=conflicts,
            conflicted_claims=conflicted_claims,
            limitations=limitations,
            assumptions=assumptions,
            remaining_gaps=remaining_gaps,
            answer=answer,
        )


def _evidence_ids(
    relations: tuple[GraphEvidenceRelation, ...], kind: EvidenceRelationKind
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {item.evidence_artifact_id for item in relations if item.relation is kind}
        )
    )


def _confidence(
    support: tuple[str, ...],
    opposition: tuple[str, ...],
    ambiguous: tuple[str, ...],
    conflicts: tuple[str, ...],
    assumptions: tuple[str, ...],
    deficiencies: tuple[str, ...],
) -> GraphConfidenceBasis:
    denominator = sum(
        len(items)
        for items in (
            support,
            opposition,
            ambiguous,
            conflicts,
            assumptions,
            deficiencies,
        )
    )
    score = 0.0 if denominator == 0 else round(len(support) / denominator, 6)
    payload = {
        "support_evidence_artifact_ids": support,
        "opposition_evidence_artifact_ids": opposition,
        "ambiguous_evidence_artifact_ids": ambiguous,
        "declared_conflict_artifact_ids": conflicts,
        "material_assumption_artifact_ids": assumptions,
        "open_deficiency_artifact_ids": deficiencies,
        "score": score,
        "level": _confidence_level(score).value,
        "calculation": "support/(support+opposition+ambiguity+declared_conflicts+material_assumptions+open_deficiencies)",
    }
    return GraphConfidenceBasis(
        artifact_id=content_artifact_id(payload),
        support_evidence_artifact_ids=support,
        opposition_evidence_artifact_ids=opposition,
        ambiguous_evidence_artifact_ids=ambiguous,
        declared_conflict_artifact_ids=conflicts,
        material_assumption_artifact_ids=assumptions,
        open_deficiency_artifact_ids=deficiencies,
        score=score,
        level=_confidence_level(score),
    )


def _confidence_level(score: float) -> SynthesisConfidenceLevel:
    if score == 0:
        return SynthesisConfidenceLevel.unsupported
    if score < 0.5:
        return SynthesisConfidenceLevel.low
    if score < 0.8:
        return SynthesisConfidenceLevel.moderate
    return SynthesisConfidenceLevel.high


def _conflicts(
    conflicted_claims: tuple[SynthesizedGraphClaim, ...],
    declared: tuple[ClaimConflictDeclaration, ...],
    relations_by_claim: dict[str, list[GraphEvidenceRelation]],
    resolve: Callable[[str], str],
) -> tuple[VerifiedGraphConflict, ...]:
    result = []
    for claim in conflicted_claims:
        sources = tuple(
            sorted(
                item.artifact_id
                for item in relations_by_claim[claim.canonical_claim_artifact_id]
                if item.relation is EvidenceRelationKind.opposes
            )
        )
        if not sources:
            continue
        result.append(
            _conflict(
                (claim.canonical_claim_artifact_id,),
                "Verified evidence both supports and opposes this canonical claim.",
                sources,
            )
        )
    for item in declared:
        canonical_ids = tuple(
            sorted({resolve(claim_id) for claim_id in item.claim_artifact_ids})
        )
        statement = f"{item.summary} Scope: {item.scope_note}"
        result.append(_conflict(canonical_ids, statement, (item.artifact_id,)))
    unique = {item.artifact_id: item for item in result}
    return tuple(sorted(unique.values(), key=lambda item: item.artifact_id))


def _conflict(
    claim_ids: tuple[str, ...], statement: str, source_ids: tuple[str, ...]
) -> VerifiedGraphConflict:
    payload = {
        "canonical_claim_artifact_ids": claim_ids,
        "statement": statement,
        "source_artifact_ids": source_ids,
    }
    return VerifiedGraphConflict(
        artifact_id=content_artifact_id(payload),
        canonical_claim_artifact_ids=claim_ids,
        statement=statement,
        source_artifact_ids=source_ids,
    )


def _limitations(
    *,
    graph_id: str,
    claim_merge_artifact_id: str,
    contexts: dict[str, ClaimContextAnnotation],
    insufficiency: AssumptionInsufficiencyDelta,
    convergence: ConvergenceDecision,
    resolve: Callable[[str], str],
) -> tuple[GraphSynthesisLimitation, ...]:
    result = []
    for canonical_id, context in sorted(contexts.items()):
        for statement in context.uncertainty + context.limitations:
            result.append(
                _limitation(statement, (canonical_id,), (context.artifact_id,))
            )
    for assessment in insufficiency.insufficiencies:
        if assessment.outcome is InsufficiencyOutcome.sufficient:
            continue
        claim_ids = tuple(
            sorted({resolve(item) for item in assessment.claim_artifact_ids})
        )
        for statement in assessment.missing_information:
            result.append(_limitation(statement, claim_ids, (assessment.artifact_id,)))
    if convergence.outcome is not ConvergenceOutcome.converged:
        result.append(
            _limitation(
                "Research stopped with outcome "
                f"{convergence.outcome.value}; unresolved state constrains the answer.",
                (),
                (convergence.artifact_id,),
            )
        )
    if not result:
        result.append(
            _limitation(
                "Applicability beyond the canonical claims' declared qualifications was not assessed.",
                (),
                (graph_id, claim_merge_artifact_id),
            )
        )
    unique = {item.artifact_id: item for item in result}
    return tuple(sorted(unique.values(), key=lambda item: item.artifact_id))


def _limitation(
    statement: str, claim_ids: tuple[str, ...], source_ids: tuple[str, ...]
) -> GraphSynthesisLimitation:
    payload = {
        "statement": " ".join(statement.split()),
        "canonical_claim_artifact_ids": tuple(sorted(set(claim_ids))),
        "source_artifact_ids": tuple(sorted(set(source_ids))),
    }
    return GraphSynthesisLimitation(
        artifact_id=content_artifact_id(payload),
        statement=str(payload["statement"]),
        canonical_claim_artifact_ids=tuple(sorted(set(claim_ids))),
        source_artifact_ids=tuple(sorted(set(source_ids))),
    )


def _outcome(
    *,
    claims: tuple[SynthesizedGraphClaim, ...],
    conflicts: tuple[VerifiedGraphConflict, ...],
    assumptions: tuple[GraphAssumption, ...],
    gaps: tuple[ResearchDeficiency, ...],
    convergence: ConvergenceDecision,
) -> ResearchSynthesisOutcome:
    if not claims:
        return ResearchSynthesisOutcome.insufficient
    material_assumptions = any(
        item.status is not AssumptionStatus.tested for item in assumptions
    )
    if (
        convergence.outcome is ConvergenceOutcome.converged
        and not conflicts
        and not material_assumptions
        and not gaps
    ):
        return ResearchSynthesisOutcome.answered
    return ResearchSynthesisOutcome.partial


def _render_answer(
    *,
    question: str,
    outcome: ResearchSynthesisOutcome,
    consensus: tuple[SynthesizedGraphClaim, ...],
    conflicts: tuple[VerifiedGraphConflict, ...],
    conflicted_claims: tuple[SynthesizedGraphClaim, ...],
    limitations: tuple[GraphSynthesisLimitation, ...],
    assumptions: tuple[GraphAssumption, ...],
    remaining_gaps: tuple[ResearchDeficiency, ...],
) -> str:
    lines = [f"Question: {question}", f"Outcome: {outcome.value}"]
    lines.extend(_claim_section("Consensus", consensus))
    lines.extend(_claim_section("Conflicted claims", conflicted_claims))
    lines.append("Conflicts:")
    lines.extend(
        (
            f"- {item.statement} [conflict={item.artifact_id}; "
            f"claims={','.join(item.canonical_claim_artifact_ids)}; "
            f"sources={','.join(item.source_artifact_ids)}]"
        )
        for item in conflicts
    )
    if not conflicts:
        lines.append("- none admitted")
    lines.append("Limitations:")
    lines.extend(
        f"- {item.statement} [limitation={item.artifact_id}; sources={','.join(item.source_artifact_ids)}]"
        for item in limitations
    )
    lines.append("Assumptions:")
    lines.extend(
        f"- {item.statement} [status={item.status.value}; assumption={item.artifact_id}]"
        for item in assumptions
    )
    if not assumptions:
        lines.append("- none admitted")
    lines.append("Remaining gaps:")
    lines.extend(
        f"- {item.description} Required action: {item.required_action} "
        f"[status={item.status.value}; gap={item.artifact_id}]"
        for item in remaining_gaps
    )
    if not remaining_gaps:
        lines.append("- none open")
    return "\n".join(lines)


def _claim_section(
    heading: str, claims: tuple[SynthesizedGraphClaim, ...]
) -> tuple[str, ...]:
    lines = [f"{heading}:"]
    lines.extend(
        f"- {item.statement} [claim={item.artifact_id}; canonical={item.canonical_claim_artifact_id}; "
        f"confidence={item.confidence.level.value}:{item.confidence.score}; "
        f"confidence_basis={item.confidence.artifact_id}; "
        f"evidence={','.join(item.evidence_artifact_ids)}]"
        for item in claims
    )
    if not claims:
        lines.append("- none admitted")
    return tuple(lines)


__all__ = [
    "GraphConfidenceBasis",
    "GraphSynthesisError",
    "GraphSynthesisErrorCode",
    "GraphSynthesisLimitation",
    "SynthesisClaimSection",
    "SynthesisConfidenceLevel",
    "ResearchSynthesisOutcome",
    "SynthesizedGraphClaim",
    "VerifiedGraphConflict",
    "VerifiedGraphSynthesis",
    "VerifiedGraphSynthesisService",
]
