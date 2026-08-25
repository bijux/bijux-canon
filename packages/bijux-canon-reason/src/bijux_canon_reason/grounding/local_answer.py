# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Provider-free grounded answer workflow owned by the Reason package."""

from __future__ import annotations

import re
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.abstention import (
    GroundingAdmissionDecision,
    GroundingAdmissionOutcome,
    GroundingAdmissionService,
    GroundingRequestStatus,
)
from bijux_canon_reason.grounding.citation_linking import (
    CitationSourceDescriptor,
    ClaimCitationLinker,
    ClaimCitationSet,
)
from bijux_canon_reason.grounding.citation_presentation import (
    CitationPresentation,
    CitationPresentationService,
    render_citation_reference,
)
from bijux_canon_reason.grounding.citation_verification import (
    CitationVerificationReport,
    DeterministicCitationVerifier,
)
from bijux_canon_reason.grounding.claim_normalization import (
    AtomicClaimNormalizer,
    NormalizedClaimSet,
)
from bijux_canon_reason.grounding.context_representation import (
    AnswerAnnotationKind,
    ClaimConflictDeclaration,
    ClaimPresentationRole,
    ConflictRelationship,
    GroundingContextService,
    NuancedGroundingRepresentation,
    SourceQualityGrade,
    create_answer_annotation,
    create_claim_conflict,
    create_claim_context,
    render_contextualized_answer,
)
from bijux_canon_reason.grounding.evidence_packets import EvidencePacket
from bijux_canon_reason.grounding.evidence_state import (
    GroundingEvidenceState,
    RetrievalEvidenceStatus,
    VexEvidenceStatus,
)
from bijux_canon_reason.grounding.extractive_synthesis import (
    CredentialFreeSynthesis,
    CredentialFreeSynthesisPolicy,
    CredentialFreeSynthesizer,
    EvidenceRole,
    SemanticEmbeddingService,
    SynthesisStyle,
    infer_synthesis_style,
    recommended_point_count,
    required_source_count,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class LocalGroundedAnswer(StableModel):
    """One content-addressed local answer with complete grounding decisions."""

    schema_version: str = "bijux.canon.reason.local_grounded_answer.v4"
    artifact_id: str
    answer_text: str
    outcome: GroundingAdmissionOutcome
    synthesis: CredentialFreeSynthesis
    claims: NormalizedClaimSet
    citations: ClaimCitationSet
    citation_presentation: CitationPresentation
    verification: CitationVerificationReport
    admission: GroundingAdmissionDecision
    contextualized: NuancedGroundingRepresentation
    evidence_state: GroundingEvidenceState

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("answer_text")
    @classmethod
    def _validate_answer(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("local grounded answer text must not be empty")
        return value

    @model_validator(mode="after")
    def _validate_lineage(self) -> Self:
        if (
            self.claims.source_synthesis_artifact_id != self.synthesis.artifact_id
            or self.citations.source_claim_set_artifact_id != self.claims.artifact_id
            or self.verification.source_claim_set_artifact_id != self.claims.artifact_id
            or self.citation_presentation.source_claim_set_artifact_id
            != self.claims.artifact_id
            or self.citation_presentation.claim_citation_set_artifact_id
            != self.citations.artifact_id
            or self.admission.source_claim_set_artifact_id != self.claims.artifact_id
            or self.contextualized.source_claim_set_artifact_id
            != self.claims.artifact_id
            or self.contextualized.citation_presentation_artifact_id
            != self.citation_presentation.artifact_id
            or self.admission.evidence_state_artifact_id
            != self.evidence_state.artifact_id
        ):
            raise ValueError("local grounded answer lineage diverged")
        if self.outcome is not self.admission.outcome:
            raise ValueError("local grounded answer outcome diverged from admission")
        if self.outcome is GroundingAdmissionOutcome.abstained and any(
            claim.statement in self.answer_text for claim in self.claims.claims
        ):
            raise ValueError("abstained local answer leaked an unadmitted claim")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("local grounded answer identity does not match")
        return self


class LocalGroundedAnswerService:
    """Synthesize, verify, contextualize, and admit one closed evidence packet."""

    def __init__(
        self,
        *,
        semantic_encoder: SemanticEmbeddingService | None = None,
    ) -> None:
        self._semantic_encoder = semantic_encoder

    def answer(
        self,
        *,
        question: str,
        evidence_packet: EvidencePacket,
        sources: tuple[CitationSourceDescriptor, ...],
        max_points: int,
        evidence_state: GroundingEvidenceState | None = None,
        synthesis_style: SynthesisStyle | None = None,
        retain_cross_source_corroboration: bool = False,
        request_status: GroundingRequestStatus | None = None,
    ) -> LocalGroundedAnswer:
        """Execute the deterministic provider-free answer workflow."""

        effective_evidence_state = evidence_state or GroundingEvidenceState.create(
            retrieval_status=(
                RetrievalEvidenceStatus.success
                if evidence_packet.selected
                else RetrievalEvidenceStatus.insufficient
            ),
            vex_status=VexEvidenceStatus.not_applicable,
            retrieved_evidence_count=len(evidence_packet.selected),
            selected_evidence_count=len(evidence_packet.selected),
            packet_completeness=evidence_packet.completeness,
        )
        style = synthesis_style or infer_synthesis_style(question)
        synthesis = CredentialFreeSynthesizer(
            CredentialFreeSynthesisPolicy(
                max_points=min(max_points, recommended_point_count(question)),
                required_sources=required_source_count(question),
                retain_cross_source_corroboration=(retain_cross_source_corroboration),
                semantic_encoder_id=(
                    None
                    if self._semantic_encoder is None
                    else self._semantic_encoder.model_lock_id
                ),
            ),
            semantic_encoder=self._semantic_encoder,
        ).synthesize(
            question=question,
            evidence_packet=evidence_packet,
            style=style,
        )
        claims = AtomicClaimNormalizer().normalize_credential_free(synthesis)
        citations = ClaimCitationLinker().link(
            claim_set=claims,
            evidence_packet=evidence_packet,
            sources=sources,
        )
        verification = DeterministicCitationVerifier().verify(
            claim_set=claims,
            citation_set=citations,
            evidence_packet=evidence_packet,
            sources=sources,
        )
        citation_presentation = CitationPresentationService().present(citations)
        admission = GroundingAdmissionService().decide(
            claim_set=claims,
            citation_set=citations,
            verification_report=verification,
            request_status=request_status or _request_status(question),
            evidence_state=effective_evidence_state,
        )
        contextualized = self._contextualize(
            synthesis=synthesis,
            claims=claims,
            citations=citations,
            verification=verification,
        )
        answer_text = render_grounded_answer(
            synthesis=synthesis,
            claims=claims,
            citations=citations,
            admission=admission,
            citation_presentation=citation_presentation,
            contextualized=contextualized,
        )
        payload = {
            "schema_version": "bijux.canon.reason.local_grounded_answer.v4",
            "answer_text": answer_text,
            "outcome": admission.outcome.value,
            "synthesis": synthesis.model_dump(mode="json"),
            "claims": claims.model_dump(mode="json"),
            "citations": citations.model_dump(mode="json"),
            "citation_presentation": citation_presentation.model_dump(mode="json"),
            "verification": verification.model_dump(mode="json"),
            "admission": admission.model_dump(mode="json"),
            "contextualized": contextualized.model_dump(mode="json"),
            "evidence_state": effective_evidence_state.model_dump(mode="json"),
        }
        return LocalGroundedAnswer(
            artifact_id=content_artifact_id(payload),
            answer_text=answer_text,
            outcome=admission.outcome,
            synthesis=synthesis,
            claims=claims,
            citations=citations,
            citation_presentation=citation_presentation,
            verification=verification,
            admission=admission,
            contextualized=contextualized,
            evidence_state=effective_evidence_state,
        )

    @staticmethod
    def _contextualize(
        *,
        synthesis: CredentialFreeSynthesis,
        claims: NormalizedClaimSet,
        citations: ClaimCitationSet,
        verification: CitationVerificationReport,
    ) -> NuancedGroundingRepresentation:
        links_by_claim = {
            claim.artifact_id: tuple(
                link
                for link in citations.links
                if link.claim_artifact_id == claim.artifact_id
            )
            for claim in claims.claims
        }
        contexts = []
        roles_by_claim: dict[str, ClaimPresentationRole] = {}
        for claim in claims.claims:
            point = synthesis.points[claim.source_candidate_ordinal - 1]
            presentation_role = _presentation_role(point.role)
            roles_by_claim[claim.artifact_id] = presentation_role
            qualification = claim.qualification
            links = links_by_claim[claim.artifact_id]
            section_paths = tuple(" / ".join(link.section_path) for link in links) or (
                "section unavailable",
            )
            contexts.append(
                create_claim_context(
                    claim_artifact_id=claim.artifact_id,
                    population_scope=(
                        qualification.population_scope
                        or (f"source-scoped: {claim.scope}",)
                    ),
                    method_scope=section_paths,
                    temporal_scope=(
                        qualification.temporal_scope
                        or ("no explicit temporal qualifier in the claim",)
                    ),
                    uncertainty=_claim_uncertainty(
                        qualification.modality.value,
                        negated=qualification.negated,
                        counterevidence=(point.role is EvidenceRole.counterevidence),
                    ),
                    limitations=(
                        "claim remains limited to its exact source scope",
                        f"evidence role: {point.role.value}",
                        "explicit quantities: "
                        + (", ".join(qualification.quantitative_scope) or "none"),
                    ),
                    source_quality=SourceQualityGrade.unknown,
                    source_quality_basis=(
                        "citation integrity is verified; study quality was not inferred"
                    ),
                    presentation_role=presentation_role,
                )
            )
        conflicts: tuple[ClaimConflictDeclaration, ...] = ()
        finding_ids = tuple(
            claim.artifact_id
            for claim in claims.claims
            if roles_by_claim[claim.artifact_id] is ClaimPresentationRole.finding
        )
        counterevidence_ids = tuple(
            claim.artifact_id
            for claim in claims.claims
            if roles_by_claim[claim.artifact_id]
            is ClaimPresentationRole.counterevidence
        )
        explicit_polarities = {claim.qualification.negated for claim in claims.claims}
        explicit_conflict_ids = (
            tuple(claim.artifact_id for claim in claims.claims)
            if synthesis.style is SynthesisStyle.conflict_preserving
            and explicit_polarities == {False, True}
            else ()
        )
        conflict_ids = (
            (*finding_ids, *counterevidence_ids)
            if finding_ids and counterevidence_ids
            else explicit_conflict_ids
        )
        if conflict_ids:
            conflicts = (
                create_claim_conflict(
                    relationship=ConflictRelationship.divergent,
                    claim_artifact_ids=conflict_ids,
                    summary=(
                        "The retrieved findings and counterevidence remain unresolved "
                        "and are not collapsed by majority vote."
                    ),
                    scope_note=(
                        "Each record retains its explicit population, method, and "
                        "temporal scope; scientific equivalence is not assumed."
                    ),
                ),
            )
        annotations = tuple(
            create_answer_annotation(
                kind=AnswerAnnotationKind.answer_limitation,
                statement=item,
                basis_artifact_ids=(synthesis.artifact_id,),
            )
            for item in synthesis.limitations
        )
        return GroundingContextService().represent(
            claim_set=claims,
            citation_set=citations,
            verification_report=verification,
            contexts=tuple(contexts),
            conflicts=conflicts,
            annotations=annotations,
        )


def _request_status(question: str) -> GroundingRequestStatus:
    normalized = " ".join(question.casefold().split())
    categorical = normalized.startswith(("are ", "can ", "do ", "does ", "is "))
    if categorical and normalized.endswith("?"):
        terms = re.findall(r"[^\W_]+", normalized)
        contextual = {
            "article",
            "condition",
            "experiment",
            "sample",
            "samples",
            "specimen",
            "specimens",
            "study",
            "treatment",
        }
        asks_for_proof = bool(re.search(r"\bprove(?:s|d)?\b", normalized))
        if len(terms) <= 12 and (asks_for_proof or not contextual.intersection(terms)):
            return GroundingRequestStatus.clarification_required
    return GroundingRequestStatus.in_scope


def _claim_uncertainty(
    modality: str, *, negated: bool, counterevidence: bool
) -> tuple[str, ...]:
    annotations = [f"explicit modality: {modality}"]
    if negated:
        annotations.append("explicit negation retained")
    if counterevidence:
        annotations.append("candidate selected as counterevidence")
    return tuple(annotations)


def render_grounded_answer(
    *,
    synthesis: CredentialFreeSynthesis,
    claims: NormalizedClaimSet,
    citations: ClaimCitationSet,
    admission: GroundingAdmissionDecision,
    citation_presentation: CitationPresentation,
    contextualized: NuancedGroundingRepresentation,
) -> str:
    """Render only claims admitted by the recorded grounding decision."""

    if (
        claims.source_synthesis_artifact_id != synthesis.artifact_id
        or contextualized.source_claim_set_artifact_id != claims.artifact_id
        or contextualized.claim_citation_set_artifact_id != citations.artifact_id
        or contextualized.citation_presentation_artifact_id
        != citation_presentation.artifact_id
    ):
        raise ValueError("grounded answer presentation lineage diverged")

    if admission.outcome is GroundingAdmissionOutcome.admitted:
        return _append_references(
            render_contextualized_answer(
                nodes=contextualized.nodes,
                contexts=contextualized.contexts,
                scope_groups=contextualized.scope_groups,
                conflicts=contextualized.conflicts,
                annotations=contextualized.annotations,
                citation_set=citations,
                citation_presentation=citation_presentation,
                admitted_claim_artifact_ids=frozenset(
                    admission.admitted_claim_artifact_ids
                ),
            ),
            citation_presentation=citation_presentation,
            admitted_claim_artifact_ids=set(admission.admitted_claim_artifact_ids),
        )
    if admission.outcome is GroundingAdmissionOutcome.abstained:
        details = " ".join(gap.detail for gap in admission.evidence_gaps)
        actions = " ".join(gap.required_action for gap in admission.evidence_gaps)
        return f"Insufficient evidence. {details} Next action: {actions}"
    admitted = set(admission.admitted_claim_artifact_ids)
    lines = [
        render_contextualized_answer(
            nodes=contextualized.nodes,
            contexts=contextualized.contexts,
            scope_groups=contextualized.scope_groups,
            conflicts=contextualized.conflicts,
            annotations=contextualized.annotations,
            citation_set=citations,
            citation_presentation=citation_presentation,
            admitted_claim_artifact_ids=frozenset(admitted),
        ),
        "Unresolved evidence gaps:",
    ]
    lines.extend(f"- {gap.detail}" for gap in admission.evidence_gaps)
    return _append_references(
        "\n".join(lines),
        citation_presentation=citation_presentation,
        admitted_claim_artifact_ids=admitted,
    )


def _presentation_role(role: EvidenceRole) -> ClaimPresentationRole:
    return {
        EvidenceRole.finding: ClaimPresentationRole.finding,
        EvidenceRole.context: ClaimPresentationRole.finding,
        EvidenceRole.method: ClaimPresentationRole.method,
        EvidenceRole.limitation: ClaimPresentationRole.limitation,
        EvidenceRole.counterevidence: ClaimPresentationRole.counterevidence,
    }[role]


def _append_references(
    answer_text: str,
    *,
    citation_presentation: CitationPresentation,
    admitted_claim_artifact_ids: set[str] | None,
) -> str:
    entries = tuple(
        entry
        for entry in citation_presentation.entries
        if admitted_claim_artifact_ids is None
        or bool(set(entry.claim_artifact_ids) & admitted_claim_artifact_ids)
    )
    if not entries:
        return answer_text
    return (
        answer_text
        + "\nCitations:\n"
        + "\n".join(render_citation_reference(entry) for entry in entries)
    )


__all__ = [
    "LocalGroundedAnswer",
    "LocalGroundedAnswerService",
    "render_grounded_answer",
]
