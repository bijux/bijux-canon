# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Evidence-caused revision of an already grounded local answer."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding import (
    CitationEvidence,
    CitationSourceDescriptor,
    EvidencePacket,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    GroundingAdmissionOutcome,
    GroundingEvidenceState,
    LocalGroundedAnswer,
    LocalGroundedAnswerService,
    RetrievalEvidenceStatus,
    SynthesisStyle,
    VexEvidenceStatus,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)
from bijux_canon_reason.research.candidate_adjudication import (
    ResearchCandidateClassification,
    ResearchCandidateRelation,
)


class ClaimRevisionActionKind(StrEnum):
    """Typed change to the user-visible claim graph."""

    ADD = "add"
    REMOVE = "remove"
    QUALIFY = "qualify"
    SPLIT = "split"
    MERGE = "merge"
    STRENGTHEN = "strengthen"
    ABSTAIN = "abstain"
    PRESERVE = "preserve"


class ResearchRevisionOutcome(StrEnum):
    """Disposition of one evidence-caused answer revision."""

    REVISED = "revised"
    PRESERVED = "preserved"
    ABSTAINED = "abstained"


class ClaimRevisionAction(StableModel):
    """One immutable before/after claim change with exact evidence causes."""

    schema_version: Literal["bijux.canon.reason.claim_revision_action.v1"] = (
        "bijux.canon.reason.claim_revision_action.v1"
    )
    artifact_id: str
    kind: ClaimRevisionActionKind
    prior_claim_artifact_ids: tuple[str, ...]
    revised_claim_artifact_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    classification_artifact_ids: tuple[str, ...]
    rationale: str

    @classmethod
    def create(
        cls,
        *,
        kind: ClaimRevisionActionKind,
        prior_claim_artifact_ids: tuple[str, ...],
        revised_claim_artifact_ids: tuple[str, ...],
        evidence_artifact_ids: tuple[str, ...],
        classification_artifact_ids: tuple[str, ...],
        rationale: str,
    ) -> Self:
        payload = {
            "schema_version": "bijux.canon.reason.claim_revision_action.v1",
            "kind": kind.value,
            "prior_claim_artifact_ids": prior_claim_artifact_ids,
            "revised_claim_artifact_ids": revised_claim_artifact_ids,
            "evidence_artifact_ids": evidence_artifact_ids,
            "classification_artifact_ids": classification_artifact_ids,
            "rationale": " ".join(rationale.split()),
        }
        return cls.model_validate(
            {"artifact_id": content_artifact_id(payload), **payload}
        )

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "prior_claim_artifact_ids",
        "revised_claim_artifact_ids",
        "evidence_artifact_ids",
        "classification_artifact_ids",
    )
    @classmethod
    def _validate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("revision action identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_action(self) -> Self:
        prior_count = len(self.prior_claim_artifact_ids)
        revised_count = len(self.revised_claim_artifact_ids)
        shape_is_valid = {
            ClaimRevisionActionKind.ADD: prior_count == 0 and revised_count > 0,
            ClaimRevisionActionKind.REMOVE: prior_count > 0 and revised_count == 0,
            ClaimRevisionActionKind.QUALIFY: prior_count > 0 and revised_count > 0,
            ClaimRevisionActionKind.SPLIT: prior_count == 1 and revised_count > 1,
            ClaimRevisionActionKind.MERGE: prior_count > 1 and revised_count == 1,
            ClaimRevisionActionKind.STRENGTHEN: (
                prior_count > 0 and revised_count > 0
            ),
            ClaimRevisionActionKind.ABSTAIN: revised_count == 0,
            ClaimRevisionActionKind.PRESERVE: prior_count == revised_count,
        }[self.kind]
        if not shape_is_valid:
            raise ValueError("revision action claim shape is invalid")
        if not self.rationale or self.rationale != " ".join(self.rationale.split()):
            raise ValueError("revision action rationale must be normalized")
        if self.kind not in {
            ClaimRevisionActionKind.PRESERVE,
            ClaimRevisionActionKind.REMOVE,
        } and not self.classification_artifact_ids:
            raise ValueError("evidence-caused revision requires a classification")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("revision action identity does not match")
        return self


class ResearchAnswerRevision(StableModel):
    """Closed revised answer with preserved history and repeated verification."""

    schema_version: Literal["bijux.canon.reason.research_answer_revision.v1"] = (
        "bijux.canon.reason.research_answer_revision.v1"
    )
    artifact_id: str
    prior_claim_graph_artifact_id: str
    prior_grounded_answer_artifact_id: str
    prior_claim_artifact_ids: tuple[str, ...]
    classification_artifact_ids: tuple[str, ...]
    candidate_evidence_artifact_ids: tuple[str, ...]
    outcome: ResearchRevisionOutcome
    actions: tuple[ClaimRevisionAction, ...]
    before_answer: str
    after_answer: str
    revised_answer: LocalGroundedAnswer
    resolved_classification_artifact_ids: tuple[str, ...]
    unresolved_classification_artifact_ids: tuple[str, ...]
    summary: str

    @field_validator(
        "artifact_id",
        "prior_claim_graph_artifact_id",
        "prior_grounded_answer_artifact_id",
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_revision(self) -> Self:
        classification_ids = set(self.classification_artifact_ids)
        if set(self.resolved_classification_artifact_ids) | set(
            self.unresolved_classification_artifact_ids
        ) != classification_ids or set(self.resolved_classification_artifact_ids) & set(
            self.unresolved_classification_artifact_ids
        ):
            raise ValueError("revision classification accounting is incomplete")
        if any(
            not set(action.classification_artifact_ids) <= classification_ids
            for action in self.actions
        ):
            raise ValueError("revision action references an unknown classification")
        expected_outcome = (
            ResearchRevisionOutcome.ABSTAINED
            if self.revised_answer.outcome is GroundingAdmissionOutcome.abstained
            else ResearchRevisionOutcome.REVISED
            if self.before_answer != self.after_answer
            else ResearchRevisionOutcome.PRESERVED
        )
        if self.outcome is not expected_outcome:
            raise ValueError("revision outcome differs from the verified answer")
        if self.after_answer != self.revised_answer.answer_text:
            raise ValueError("revision after-answer differs from verified rendering")
        if not self.actions or not self.summary.strip():
            raise ValueError("revision requires actions and a concise summary")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("research answer revision identity does not match")
        return self


class ResearchAnswerRevisionService:
    """Re-synthesize and re-verify an answer from classified new evidence."""

    def revise(
        self,
        *,
        prior_claim_graph_artifact_id: str,
        prior_answer: LocalGroundedAnswer,
        prior_evidence_packet: EvidencePacket,
        classifications: tuple[ResearchCandidateClassification, ...],
        candidate_evidence: tuple[CitationEvidence, ...],
        sources: tuple[CitationSourceDescriptor, ...],
    ) -> ResearchAnswerRevision:
        """Return one closed revision or fail when lineage is incomplete."""

        require_artifact_id(prior_claim_graph_artifact_id)
        evidence_by_id = {item.artifact_id: item for item in candidate_evidence}
        classified_evidence_ids = {
            item.evidence_artifact_id for item in classifications
        }
        if set(evidence_by_id) != classified_evidence_ids:
            raise ValueError("revision candidates and classifications differ")
        for classification in classifications:
            evidence = evidence_by_id[classification.evidence_artifact_id]
            if (
                classification.locator_artifact_id != evidence.locator.artifact_id
                or classification.exact_text_sha256 != evidence.exact_text_sha256
            ):
                raise ValueError("classification is not bound to exact candidate text")

        material = tuple(item for item in classifications if item.material)
        unresolved = tuple(
            item
            for item in material
            if item.relation
            in {
                ResearchCandidateRelation.AMBIGUOUS,
                ResearchCandidateRelation.UNCLASSIFIED,
            }
        )
        usable = tuple(
            evidence_by_id[item.evidence_artifact_id]
            for item in material
            if item.relation is not ResearchCandidateRelation.IRRELEVANT
        )
        if (
            prior_answer.synthesis.evidence_packet_artifact_id
            != prior_evidence_packet.artifact_id
            or prior_answer.citations.evidence_packet_artifact_id
            != prior_evidence_packet.artifact_id
        ):
            raise ValueError("prior evidence packet differs from answer lineage")
        combined_evidence = _unique_evidence(prior_evidence_packet.selected, usable)
        combined_sources = _unique_sources(sources)
        packet = EvidencePacketBuilder(
            EvidencePacketPolicy(
                token_budget=max(
                    1,
                    sum(len(item.exact_text) for item in combined_evidence) + 1,
                ),
                citation_budget=max(1, len(combined_evidence)),
                claim_budget=max(1, len(combined_evidence)),
                max_per_source=max(1, len(combined_evidence)),
                max_per_section=max(1, len(combined_evidence)),
            )
        ).build(
            question_artifact_id=prior_evidence_packet.question_artifact_id,
            scope_artifact_id=prior_evidence_packet.scope_artifact_id,
            retrieval_trace_artifact_ids=tuple(
                dict.fromkeys(item.retrieval_artifact_id for item in combined_evidence)
            ),
            candidates=combined_evidence,
        )
        prior_vex_unresolved = prior_answer.evidence_state.vex_status in {
            VexEvidenceStatus.below_policy,
            VexEvidenceStatus.failed,
        }
        unsafe = bool(unresolved) or prior_vex_unresolved
        policy_detail = (
            "material research evidence remains ambiguous or unclassified"
            if unresolved
            else "the prior answer has unresolved VEX witness evidence"
            if prior_vex_unresolved
            else None
        )
        remediation = (
            "adjudicate the unresolved evidence before admitting an answer"
            if unresolved
            else "repeat retrieval with a policy-compliant exact witness"
            if prior_vex_unresolved
            else None
        )
        evidence_state = GroundingEvidenceState.create(
            retrieval_status=RetrievalEvidenceStatus.success,
            vex_status=_usable_vex_status(prior_answer.evidence_state.vex_status),
            retrieved_evidence_count=len(combined_evidence),
            selected_evidence_count=len(packet.selected),
            packet_completeness=packet.completeness,
            unsafe_or_unverified=unsafe,
            policy_detail=policy_detail,
            remediation=remediation,
        )
        style = _revision_style(material)
        revised = LocalGroundedAnswerService().answer(
            question=prior_answer.synthesis.question,
            evidence_packet=packet,
            sources=combined_sources,
            max_points=max(1, len(combined_evidence)),
            evidence_state=evidence_state,
            synthesis_style=style,
            retain_cross_source_corroboration=True,
        )
        if (
            revised.answer_text == prior_answer.answer_text
            and any(
                item.relation
                in {
                    ResearchCandidateRelation.OPPOSING,
                    ResearchCandidateRelation.LIMITING,
                }
                for item in material
            )
        ):
            evidence_state = GroundingEvidenceState.create(
                retrieval_status=RetrievalEvidenceStatus.success,
                vex_status=_usable_vex_status(prior_answer.evidence_state.vex_status),
                retrieved_evidence_count=len(combined_evidence),
                selected_evidence_count=len(packet.selected),
                packet_completeness=packet.completeness,
                unsafe_or_unverified=True,
                policy_detail="material counterevidence did not produce a revised claim graph",
                remediation="review or adjudicate the contradiction before answering",
            )
            revised = LocalGroundedAnswerService().answer(
                question=prior_answer.synthesis.question,
                evidence_packet=packet,
                sources=combined_sources,
                max_points=max(1, len(combined_evidence)),
                evidence_state=evidence_state,
                synthesis_style=style,
                retain_cross_source_corroboration=True,
            )

        actions = _revision_actions(
            prior_answer=prior_answer,
            revised_answer=revised,
            classifications=classifications,
        )
        resolved_ids = tuple(
            item.artifact_id for item in classifications if item not in unresolved
        )
        unresolved_ids = tuple(item.artifact_id for item in unresolved)
        outcome = (
            ResearchRevisionOutcome.ABSTAINED
            if revised.outcome is GroundingAdmissionOutcome.abstained
            else ResearchRevisionOutcome.REVISED
            if revised.answer_text != prior_answer.answer_text
            else ResearchRevisionOutcome.PRESERVED
        )
        summary = {
            ResearchRevisionOutcome.ABSTAINED: (
                "The prior answer was withdrawn because material evidence remains unresolved."
            ),
            ResearchRevisionOutcome.REVISED: (
                f"The answer changed through {len(actions)} evidence-linked claim action(s)."
            ),
            ResearchRevisionOutcome.PRESERVED: (
                "The answer was preserved because no classified evidence materially changed it."
            ),
        }[outcome]
        payload = {
            "schema_version": "bijux.canon.reason.research_answer_revision.v1",
            "prior_claim_graph_artifact_id": prior_claim_graph_artifact_id,
            "prior_grounded_answer_artifact_id": prior_answer.artifact_id,
            "prior_claim_artifact_ids": tuple(
                item.artifact_id for item in prior_answer.claims.claims
            ),
            "classification_artifact_ids": tuple(
                item.artifact_id for item in classifications
            ),
            "candidate_evidence_artifact_ids": tuple(evidence_by_id),
            "outcome": outcome.value,
            "actions": tuple(item.model_dump(mode="json") for item in actions),
            "before_answer": prior_answer.answer_text,
            "after_answer": revised.answer_text,
            "revised_answer": revised.model_dump(mode="json"),
            "resolved_classification_artifact_ids": resolved_ids,
            "unresolved_classification_artifact_ids": unresolved_ids,
            "summary": summary,
        }
        return ResearchAnswerRevision.model_validate(
            {"artifact_id": content_artifact_id(payload), **payload}
        )


def _unique_evidence(
    prior: tuple[CitationEvidence, ...],
    additions: tuple[CitationEvidence, ...],
) -> tuple[CitationEvidence, ...]:
    unique = {item.artifact_id: item for item in (*prior, *additions)}
    return tuple(unique.values())


def _usable_vex_status(value: VexEvidenceStatus) -> VexEvidenceStatus:
    if value in {VexEvidenceStatus.below_policy, VexEvidenceStatus.failed}:
        return VexEvidenceStatus.not_applicable
    return value


def _unique_sources(
    sources: tuple[CitationSourceDescriptor, ...],
) -> tuple[CitationSourceDescriptor, ...]:
    result: dict[str, CitationSourceDescriptor] = {}
    for source in sources:
        previous = result.get(source.source_id)
        if previous is not None and previous != source:
            raise ValueError("revision source metadata collides")
        result[source.source_id] = source
    return tuple(result.values())


def _revision_style(
    classifications: tuple[ResearchCandidateClassification, ...],
) -> SynthesisStyle:
    relations = {item.relation for item in classifications if item.material}
    if ResearchCandidateRelation.OPPOSING in relations:
        return SynthesisStyle.conflict_preserving
    if ResearchCandidateRelation.LIMITING in relations:
        return SynthesisStyle.limitations_review
    return SynthesisStyle.general


def _revision_actions(
    *,
    prior_answer: LocalGroundedAnswer,
    revised_answer: LocalGroundedAnswer,
    classifications: tuple[ResearchCandidateClassification, ...],
) -> tuple[ClaimRevisionAction, ...]:
    prior_ids = tuple(item.artifact_id for item in prior_answer.claims.claims)
    revised_ids = tuple(item.artifact_id for item in revised_answer.claims.claims)
    material = tuple(item for item in classifications if item.material)
    if revised_answer.outcome is GroundingAdmissionOutcome.abstained:
        return (
            ClaimRevisionAction.create(
                kind=ClaimRevisionActionKind.ABSTAIN,
                prior_claim_artifact_ids=prior_ids,
                revised_claim_artifact_ids=(),
                evidence_artifact_ids=tuple(item.evidence_artifact_id for item in material),
                classification_artifact_ids=tuple(item.artifact_id for item in material),
                rationale="material unresolved evidence prevents a verified answer",
            ),
        )
    if not material:
        return (
            ClaimRevisionAction.create(
                kind=ClaimRevisionActionKind.PRESERVE,
                prior_claim_artifact_ids=prior_ids,
                revised_claim_artifact_ids=revised_ids,
                evidence_artifact_ids=(),
                classification_artifact_ids=(),
                rationale="no material classified evidence changes the answer",
            ),
        )
    actions: list[ClaimRevisionAction] = []
    targeted_prior = tuple(
        dict.fromkeys(
            item.claim_artifact_id
            for item in material
            if item.claim_artifact_id is not None
        )
    )
    candidate_ids = {item.evidence_artifact_id for item in material}
    candidate_revised = tuple(
        claim.artifact_id
        for claim in revised_answer.claims.claims
        if candidate_ids & set(claim.citation_evidence_artifact_ids)
    )
    if len(targeted_prior) == 1 and len(candidate_revised) > 1:
        kind = ClaimRevisionActionKind.SPLIT
    elif len(targeted_prior) > 1 and len(candidate_revised) == 1:
        kind = ClaimRevisionActionKind.MERGE
    elif any(
        item.relation
        in {ResearchCandidateRelation.OPPOSING, ResearchCandidateRelation.LIMITING}
        for item in material
    ):
        kind = ClaimRevisionActionKind.QUALIFY
    else:
        kind = ClaimRevisionActionKind.STRENGTHEN
    if targeted_prior and candidate_revised:
        actions.append(
            ClaimRevisionAction.create(
                kind=kind,
                prior_claim_artifact_ids=targeted_prior,
                revised_claim_artifact_ids=candidate_revised,
                evidence_artifact_ids=tuple(item.evidence_artifact_id for item in material),
                classification_artifact_ids=tuple(item.artifact_id for item in material),
                rationale=(
                    "material support, opposition, or limitation changed the verified claim presentation"
                ),
            )
        )
    added = tuple(item for item in revised_ids if item not in candidate_revised)
    if added and not actions:
        actions.append(
            ClaimRevisionAction.create(
                kind=ClaimRevisionActionKind.ADD,
                prior_claim_artifact_ids=(),
                revised_claim_artifact_ids=added,
                evidence_artifact_ids=tuple(candidate_ids),
                classification_artifact_ids=tuple(item.artifact_id for item in material),
                rationale="new classified evidence added verified claims",
            )
        )
    removed = tuple(item for item in prior_ids if item not in targeted_prior)
    if removed and not revised_ids:
        actions.append(
            ClaimRevisionAction.create(
                kind=ClaimRevisionActionKind.REMOVE,
                prior_claim_artifact_ids=removed,
                revised_claim_artifact_ids=(),
                evidence_artifact_ids=tuple(candidate_ids),
                classification_artifact_ids=(),
                rationale="re-verification removed claims that are no longer admissible",
            )
        )
    if not actions:
        actions.append(
            ClaimRevisionAction.create(
                kind=ClaimRevisionActionKind.PRESERVE,
                prior_claim_artifact_ids=prior_ids,
                revised_claim_artifact_ids=revised_ids,
                evidence_artifact_ids=tuple(candidate_ids),
                classification_artifact_ids=(),
                rationale="classified evidence did not change a verified claim",
            )
        )
    return tuple(actions)


__all__ = [
    "ClaimRevisionAction",
    "ClaimRevisionActionKind",
    "ResearchAnswerRevision",
    "ResearchAnswerRevisionService",
    "ResearchRevisionOutcome",
]
