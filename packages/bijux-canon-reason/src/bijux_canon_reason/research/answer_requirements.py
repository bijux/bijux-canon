# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Derive question-specific, inspectable answer requirements from grounded RAG."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.abstention import (
    GroundingAdmissionDecision,
    GroundingRequestStatus,
)
from bijux_canon_reason.grounding.citation_verification import (
    CitationVerificationReport,
    EntailmentVerdict,
    VerifiedAtomicClaim,
)
from bijux_canon_reason.grounding.claim_normalization import NormalizedClaimSet
from bijux_canon_reason.grounding.extractive_synthesis import (
    CredentialFreeSynthesis,
    EvidenceRole,
    SynthesisStyle,
)
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class AnswerRequirementKind(StrEnum):
    """Question-specific evidence need represented by one plan node."""

    ANSWERABILITY = "answerability"
    FINDING = "finding"
    METHOD_CONTEXT = "method_context"
    OPPOSITION = "opposition"
    LIMITATION = "limitation"
    DISAMBIGUATION = "disambiguation"
    CROSS_CLAIM_SYNTHESIS = "cross_claim_synthesis"


class AnswerRequirementStatus(StrEnum):
    """Current disposition of an answer requirement."""

    SATISFIED = "satisfied"
    UNRESOLVED = "unresolved"
    UNSEARCHABLE = "unsearchable"
    OUT_OF_SCOPE = "out_of_scope"


class AnswerRequirementPlanOutcome(StrEnum):
    """Whether the requirement plan needs additional retrieval."""

    READY_WITHOUT_SEARCH = "ready_without_search"
    SEARCH_REQUIRED = "search_required"
    BLOCKED = "blocked"


class SkepticalSearchCompletion(StableModel):
    """Exact prior skeptical search and its material-classification closure."""

    artifact_id: str
    claim_artifact_id: str
    search_run_artifact_id: str
    material_candidate_artifact_ids: tuple[str, ...]
    classified_candidate_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id", "claim_artifact_id", "search_run_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "material_candidate_artifact_ids", "classified_candidate_artifact_ids"
    )
    @classmethod
    def _validate_candidate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("skeptical search candidate identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_completion(self) -> Self:
        if not set(self.classified_candidate_artifact_ids).issubset(
            self.material_candidate_artifact_ids
        ):
            raise ValueError("classified candidates must belong to the search")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("skeptical search completion identity does not match")
        return self

    @property
    def complete(self) -> bool:
        """Return whether every material candidate has been classified."""
        return set(self.material_candidate_artifact_ids) == set(
            self.classified_candidate_artifact_ids
        )


def create_skeptical_search_completion(
    *,
    claim_artifact_id: str,
    search_run_artifact_id: str,
    material_candidate_artifact_ids: tuple[str, ...] = (),
    classified_candidate_artifact_ids: tuple[str, ...] = (),
) -> SkepticalSearchCompletion:
    """Create one immutable prior-search completion observation."""
    payload = {
        "claim_artifact_id": claim_artifact_id,
        "search_run_artifact_id": search_run_artifact_id,
        "material_candidate_artifact_ids": material_candidate_artifact_ids,
        "classified_candidate_artifact_ids": classified_candidate_artifact_ids,
    }
    return SkepticalSearchCompletion(
        artifact_id=content_artifact_id(payload),
        claim_artifact_id=claim_artifact_id,
        search_run_artifact_id=search_run_artifact_id,
        material_candidate_artifact_ids=material_candidate_artifact_ids,
        classified_candidate_artifact_ids=classified_candidate_artifact_ids,
    )


class PlannedAnswerRequirement(StableModel):
    """One stable need with exact satisfaction and dependency semantics."""

    schema_version: Literal["bijux.canon.reason.answer_requirement.v1"] = (
        "bijux.canon.reason.answer_requirement.v1"
    )
    artifact_id: str
    kind: AnswerRequirementKind
    description: str
    priority: int
    material: bool
    target_claim_artifact_ids: tuple[str, ...]
    dependency_requirement_artifact_ids: tuple[str, ...]
    satisfaction_criteria: tuple[str, ...]
    status: AnswerRequirementStatus
    query_text: str | None
    evidence_artifact_ids: tuple[str, ...]
    source_gap_artifact_ids: tuple[str, ...]

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator(
        "target_claim_artifact_ids",
        "dependency_requirement_artifact_ids",
        "evidence_artifact_ids",
        "source_gap_artifact_ids",
    )
    @classmethod
    def _validate_artifact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("answer requirement identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @field_validator("description", "query_text")
    @classmethod
    def _validate_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("answer requirement text must not be empty")
        return normalized

    @field_validator("satisfaction_criteria")
    @classmethod
    def _validate_criteria(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(" ".join(item.split()) for item in value)
        if not normalized or any(not item for item in normalized):
            raise ValueError("answer requirements need satisfaction criteria")
        if len(normalized) != len(set(normalized)):
            raise ValueError("answer requirement criteria must be unique")
        return normalized

    @model_validator(mode="after")
    def _validate_requirement(self) -> Self:
        if not 1 <= self.priority <= 100:
            raise ValueError("answer requirement priority must be within 1..100")
        if self.status is AnswerRequirementStatus.SATISFIED:
            if self.query_text is not None or not self.evidence_artifact_ids:
                raise ValueError(
                    "satisfied requirements need evidence and no search query"
                )
        elif self.status is AnswerRequirementStatus.UNRESOLVED:
            if self.query_text is None:
                raise ValueError("unresolved searchable requirements need a query")
        elif self.query_text is not None:
            raise ValueError("blocked requirements cannot expose a search query")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("answer requirement identity does not match")
        return self


class AnswerRequirementPlan(StableModel):
    """Complete dependency-ordered plan for answering one exact question."""

    schema_version: Literal["bijux.canon.reason.answer_requirement_plan.v1"] = (
        "bijux.canon.reason.answer_requirement_plan.v1"
    )
    artifact_id: str
    question_artifact_id: str
    graph_artifact_id: str
    scope_artifact_id: str
    question: str
    requirements: tuple[PlannedAnswerRequirement, ...]
    search_requirement_artifact_ids: tuple[str, ...]
    outcome: AnswerRequirementPlanOutcome

    @field_validator(
        "artifact_id", "question_artifact_id", "graph_artifact_id", "scope_artifact_id"
    )
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("question")
    @classmethod
    def _validate_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("answer requirement plan needs a question")
        return normalized

    @field_validator("search_requirement_artifact_ids")
    @classmethod
    def _validate_search_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("search requirement identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_plan(self) -> Self:
        requirement_ids = tuple(item.artifact_id for item in self.requirements)
        if not requirement_ids or len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("answer requirement plan identities must be nonempty and unique")
        known: set[str] = set()
        for requirement in self.requirements:
            if any(
                dependency not in known
                for dependency in requirement.dependency_requirement_artifact_ids
            ):
                raise ValueError(
                    "answer requirement dependencies must reference earlier nodes"
                )
            known.add(requirement.artifact_id)
        expected_search = tuple(
            item.artifact_id
            for item in sorted(
                (
                    requirement
                    for requirement in self.requirements
                    if requirement.material
                    and requirement.status is AnswerRequirementStatus.UNRESOLVED
                ),
                key=lambda item: (-item.priority, item.artifact_id),
            )
        )
        if self.search_requirement_artifact_ids != expected_search:
            raise ValueError("search requirements do not match unresolved material needs")
        blocked = any(
            item.material
            and item.status
            in {
                AnswerRequirementStatus.UNSEARCHABLE,
                AnswerRequirementStatus.OUT_OF_SCOPE,
            }
            for item in self.requirements
        )
        expected_outcome = (
            AnswerRequirementPlanOutcome.BLOCKED
            if blocked
            else (
                AnswerRequirementPlanOutcome.SEARCH_REQUIRED
                if expected_search
                else AnswerRequirementPlanOutcome.READY_WITHOUT_SEARCH
            )
        )
        if self.outcome is not expected_outcome:
            raise ValueError("answer requirement plan outcome does not match needs")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("answer requirement plan identity does not match")
        return self


class AnswerRequirementPlanningService:
    """Derive a deterministic research plan from grounded claims and verdicts."""

    def plan(
        self,
        *,
        question: str,
        graph_artifact_id: str,
        scope_artifact_id: str,
        claims: NormalizedClaimSet,
        verification: CitationVerificationReport,
        admission: GroundingAdmissionDecision,
        synthesis: CredentialFreeSynthesis,
        skeptical_search_completions: tuple[SkepticalSearchCompletion, ...] = (),
    ) -> AnswerRequirementPlan:
        """Plan only evidence needs justified by the exact initial RAG state."""
        normalized_question = " ".join(question.split())
        require_artifact_id(graph_artifact_id)
        require_artifact_id(scope_artifact_id)
        if not normalized_question:
            raise ValueError("answer requirement planning needs a question")
        if synthesis.question != normalized_question:
            raise ValueError("synthesis belongs to another research question")
        if verification.source_claim_set_artifact_id != claims.artifact_id:
            raise ValueError("verification belongs to another claim set")
        if admission.source_claim_set_artifact_id != claims.artifact_id:
            raise ValueError("admission belongs to another claim set")
        claim_ids = tuple(claim.artifact_id for claim in claims.claims)
        completion_by_claim = {
            item.claim_artifact_id: item for item in skeptical_search_completions
        }
        if len(completion_by_claim) != len(skeptical_search_completions):
            raise ValueError("skeptical search completions must target unique claims")
        if not set(completion_by_claim).issubset(set(claim_ids)):
            raise ValueError("skeptical search completion references an unknown claim")

        question_id = content_artifact_id(
            {
                "question": normalized_question,
                "schema_version": "bijux.canon.reason.question.v1",
            }
        )
        terminal_status = _terminal_status(admission.request_status)
        requirements: list[PlannedAnswerRequirement] = []
        answerability = _answerability_requirement(
            question=normalized_question,
            admission=admission,
            terminal_status=terminal_status,
        )
        requirements.append(answerability)

        verified = {item.claim_artifact_id: item for item in verification.claims}
        finding_by_claim: dict[str, PlannedAnswerRequirement] = {}
        for claim in claims.claims:
            requirement = _finding_requirement(
                question=normalized_question,
                claim_id=claim.artifact_id,
                statement=claim.statement,
                verification=verified.get(claim.artifact_id),
                admission=admission,
                answerability=answerability,
                terminal_status=terminal_status,
            )
            requirements.append(requirement)
            finding_by_claim[claim.artifact_id] = requirement
        if not claims.claims:
            requirements.append(
                _global_finding_requirement(
                    question=normalized_question,
                    answerability=answerability,
                    terminal_status=terminal_status,
                    admission=admission,
                )
            )

        method = _role_requirement(
            kind=AnswerRequirementKind.METHOD_CONTEXT,
            description="Establish the methods and context needed to interpret the answer.",
            query=f"{normalized_question} methods protocol sampling analysis context",
            criterion=(
                "Directly cited method or context evidence matches the question scope."
            ),
            role=EvidenceRole.method,
            material=synthesis.style is SynthesisStyle.methods_comparison,
            priority=85,
            synthesis=synthesis,
            question_id=question_id,
            dependencies=tuple(item.artifact_id for item in finding_by_claim.values()),
            terminal_status=terminal_status,
            admission=admission,
        )
        requirements.append(method)

        for claim in claims.claims:
            finding = finding_by_claim[claim.artifact_id]
            requirements.append(
                _opposition_requirement(
                    question=normalized_question,
                    claim_id=claim.artifact_id,
                    statement=claim.statement,
                    finding=finding,
                    completion=completion_by_claim.get(claim.artifact_id),
                    terminal_status=terminal_status,
                    admission=admission,
                )
            )
            verdict = verified.get(claim.artifact_id)
            if verdict is not None and verdict.verdict is EntailmentVerdict.ambiguity:
                requirements.append(
                    _disambiguation_requirement(
                        question=normalized_question,
                        claim_id=claim.artifact_id,
                        statement=claim.statement,
                        finding=finding,
                        verification_claim_id=verdict.artifact_id,
                        admission=admission,
                    )
                )

        limitation = _role_requirement(
            kind=AnswerRequirementKind.LIMITATION,
            description="State evidence-backed limitations and corpus boundaries.",
            query=f"{normalized_question} limitations caveats sample scope uncertainty",
            criterion=(
                "The answer states limitations grounded in selected evidence or its exact corpus boundary."
            ),
            role=EvidenceRole.limitation,
            material=True,
            priority=80,
            synthesis=synthesis,
            question_id=question_id,
            dependencies=tuple(item.artifact_id for item in finding_by_claim.values()),
            terminal_status=terminal_status,
            admission=admission,
            allow_declared_limitation=True,
        )
        requirements.append(limitation)

        if synthesis.style is SynthesisStyle.multi_hop and len(finding_by_claim) > 1:
            dependencies = tuple(
                item.artifact_id for item in finding_by_claim.values()
            )
            dependency_ready = all(
                item.status is AnswerRequirementStatus.SATISFIED
                for item in finding_by_claim.values()
            )
            requirements.append(
                _requirement(
                    kind=AnswerRequirementKind.CROSS_CLAIM_SYNTHESIS,
                    description=(
                        "Connect the supported findings needed for the multi-hop answer."
                    ),
                    priority=90,
                    material=True,
                    target_claim_ids=tuple(finding_by_claim),
                    dependencies=dependencies,
                    criteria=(
                        "Every dependent finding is directly supported and their scopes are compatible.",
                    ),
                    status=(
                        AnswerRequirementStatus.SATISFIED
                        if dependency_ready
                        else AnswerRequirementStatus.UNRESOLVED
                    ),
                    query_text=(
                        None
                        if dependency_ready
                        else f"{normalized_question} relationship across findings"
                    ),
                    evidence_ids=(dependencies if dependency_ready else ()),
                    source_gap_ids=(),
                )
            )

        ordered = tuple(requirements)
        search_ids = tuple(
            item.artifact_id
            for item in sorted(
                (
                    item
                    for item in ordered
                    if item.material
                    and item.status is AnswerRequirementStatus.UNRESOLVED
                ),
                key=lambda item: (-item.priority, item.artifact_id),
            )
        )
        blocked = any(
            item.material
            and item.status
            in {
                AnswerRequirementStatus.UNSEARCHABLE,
                AnswerRequirementStatus.OUT_OF_SCOPE,
            }
            for item in ordered
        )
        outcome = (
            AnswerRequirementPlanOutcome.BLOCKED
            if blocked
            else (
                AnswerRequirementPlanOutcome.SEARCH_REQUIRED
                if search_ids
                else AnswerRequirementPlanOutcome.READY_WITHOUT_SEARCH
            )
        )
        payload = {
            "schema_version": "bijux.canon.reason.answer_requirement_plan.v1",
            "question_artifact_id": question_id,
            "graph_artifact_id": graph_artifact_id,
            "scope_artifact_id": scope_artifact_id,
            "question": normalized_question,
            "requirements": tuple(item.model_dump(mode="json") for item in ordered),
            "search_requirement_artifact_ids": search_ids,
            "outcome": outcome.value,
        }
        return AnswerRequirementPlan(
            artifact_id=content_artifact_id(payload),
            question_artifact_id=question_id,
            graph_artifact_id=graph_artifact_id,
            scope_artifact_id=scope_artifact_id,
            question=normalized_question,
            requirements=ordered,
            search_requirement_artifact_ids=search_ids,
            outcome=outcome,
        )


def _terminal_status(
    request_status: GroundingRequestStatus,
) -> AnswerRequirementStatus | None:
    if request_status is GroundingRequestStatus.out_of_scope:
        return AnswerRequirementStatus.OUT_OF_SCOPE
    if request_status in {
        GroundingRequestStatus.fabricated_entity,
        GroundingRequestStatus.corrupt_evidence,
    }:
        return AnswerRequirementStatus.UNSEARCHABLE
    return None


def _answerability_requirement(
    *,
    question: str,
    admission: GroundingAdmissionDecision,
    terminal_status: AnswerRequirementStatus | None,
) -> PlannedAnswerRequirement:
    evidence_ids: tuple[str, ...]
    query: str | None
    if terminal_status is not None:
        status = terminal_status
        evidence_ids = (admission.artifact_id,)
        query = None
    elif admission.admitted_claim_artifact_ids:
        status = AnswerRequirementStatus.SATISFIED
        evidence_ids = admission.admitted_claim_artifact_ids
        query = None
    else:
        status = AnswerRequirementStatus.UNRESOLVED
        evidence_ids = ()
        query = f"{question} direct answerable evidence in declared corpus scope"
    return _requirement(
        kind=AnswerRequirementKind.ANSWERABILITY,
        description="Determine whether the question is answerable within corpus scope.",
        priority=100,
        material=True,
        target_claim_ids=(),
        dependencies=(),
        criteria=(
            "At least one directly supported claim answers the in-scope question, or a typed scope refusal is retained.",
        ),
        status=status,
        query_text=query,
        evidence_ids=evidence_ids,
        source_gap_ids=tuple(item.artifact_id for item in admission.evidence_gaps),
    )


def _finding_requirement(
    *,
    question: str,
    claim_id: str,
    statement: str,
    verification: VerifiedAtomicClaim | None,
    admission: GroundingAdmissionDecision,
    answerability: PlannedAnswerRequirement,
    terminal_status: AnswerRequirementStatus | None,
) -> PlannedAnswerRequirement:
    evidence: tuple[str, ...]
    query: str | None
    verdict = None if verification is None else verification.verdict
    assessments = () if verification is None else verification.assessments
    direct_evidence = tuple(
        item.citation_evidence_artifact_id
        for item in assessments
        if item.verdict is EntailmentVerdict.direct_support
    )
    admitted = claim_id in admission.admitted_claim_artifact_ids
    if terminal_status is not None:
        status = terminal_status
        query = None
        evidence = (admission.artifact_id,)
    elif admitted and verdict is EntailmentVerdict.direct_support and direct_evidence:
        status = AnswerRequirementStatus.SATISFIED
        query = None
        evidence = direct_evidence
    else:
        status = AnswerRequirementStatus.UNRESOLVED
        query = f'{question} direct evidence for or against "{statement}"'
        evidence = ()
    gaps = tuple(
        item.artifact_id
        for item in admission.evidence_gaps
        if item.claim_artifact_id == claim_id
    )
    return _requirement(
        kind=AnswerRequirementKind.FINDING,
        description=f"Establish the answer claim: {statement}",
        priority=95,
        material=True,
        target_claim_ids=(claim_id,),
        dependencies=(answerability.artifact_id,),
        criteria=(
            "An exact citation directly supports the atomic claim with aligned entity, scope, quantity, modality, and negation.",
        ),
        status=status,
        query_text=query,
        evidence_ids=evidence,
        source_gap_ids=gaps,
    )


def _global_finding_requirement(
    *,
    question: str,
    answerability: PlannedAnswerRequirement,
    terminal_status: AnswerRequirementStatus | None,
    admission: GroundingAdmissionDecision,
) -> PlannedAnswerRequirement:
    status = terminal_status or AnswerRequirementStatus.UNRESOLVED
    return _requirement(
        kind=AnswerRequirementKind.FINDING,
        description="Establish at least one factual finding that answers the question.",
        priority=95,
        material=True,
        target_claim_ids=(),
        dependencies=(answerability.artifact_id,),
        criteria=("A directly supported atomic answer claim is admitted.",),
        status=status,
        query_text=None if terminal_status else f"{question} direct factual finding",
        evidence_ids=(admission.artifact_id,) if terminal_status else (),
        source_gap_ids=(
            tuple(item.artifact_id for item in admission.evidence_gaps)
        ),
    )


def _role_requirement(
    *,
    kind: AnswerRequirementKind,
    description: str,
    query: str,
    criterion: str,
    role: EvidenceRole,
    material: bool,
    priority: int,
    synthesis: CredentialFreeSynthesis,
    question_id: str,
    dependencies: tuple[str, ...],
    terminal_status: AnswerRequirementStatus | None,
    admission: GroundingAdmissionDecision,
    allow_declared_limitation: bool = False,
) -> PlannedAnswerRequirement:
    evidence: tuple[str, ...]
    query_text: str | None
    role_evidence = tuple(
        point.citation_evidence_artifact_id
        for point in synthesis.points
        if point.role is role
    )
    declared = allow_declared_limitation and bool(synthesis.limitations)
    if terminal_status is not None:
        status = terminal_status
        evidence = (admission.artifact_id,)
        query_text = None
    elif role_evidence or declared or not material:
        status = AnswerRequirementStatus.SATISFIED
        evidence = role_evidence or (
            (synthesis.artifact_id,) if declared else (question_id,)
        )
        query_text = None
    else:
        status = AnswerRequirementStatus.UNRESOLVED
        evidence = ()
        query_text = query
    return _requirement(
        kind=kind,
        description=description,
        priority=priority,
        material=material,
        target_claim_ids=(),
        dependencies=dependencies,
        criteria=(criterion,),
        status=status,
        query_text=query_text,
        evidence_ids=evidence,
        source_gap_ids=(),
    )


def _opposition_requirement(
    *,
    question: str,
    claim_id: str,
    statement: str,
    finding: PlannedAnswerRequirement,
    completion: SkepticalSearchCompletion | None,
    terminal_status: AnswerRequirementStatus | None,
    admission: GroundingAdmissionDecision,
) -> PlannedAnswerRequirement:
    evidence: tuple[str, ...]
    query: str | None
    if terminal_status is not None:
        status = terminal_status
        evidence = (admission.artifact_id,)
        query = None
    elif completion is not None and completion.complete:
        status = AnswerRequirementStatus.SATISFIED
        evidence = (completion.artifact_id, completion.search_run_artifact_id)
        query = None
    else:
        status = AnswerRequirementStatus.UNRESOLVED
        evidence = () if completion is None else (completion.artifact_id,)
        query = (
            f'{question} contradictory evidence limitations alternative interpretation '
            f'for "{statement}"'
        )
    return _requirement(
        kind=AnswerRequirementKind.OPPOSITION,
        description=f"Search for material opposition to: {statement}",
        priority=90,
        material=True,
        target_claim_ids=(claim_id,),
        dependencies=(finding.artifact_id,),
        criteria=(
            "A bounded skeptical search is completed and every material candidate is classified.",
        ),
        status=status,
        query_text=query,
        evidence_ids=evidence,
        source_gap_ids=(),
    )


def _disambiguation_requirement(
    *,
    question: str,
    claim_id: str,
    statement: str,
    finding: PlannedAnswerRequirement,
    verification_claim_id: str,
    admission: GroundingAdmissionDecision,
) -> PlannedAnswerRequirement:
    gaps = tuple(
        item.artifact_id
        for item in admission.evidence_gaps
        if item.claim_artifact_id == claim_id
    )
    return _requirement(
        kind=AnswerRequirementKind.DISAMBIGUATION,
        description=f"Resolve ambiguous entity, scope, or qualifier alignment: {statement}",
        priority=98,
        material=True,
        target_claim_ids=(claim_id,),
        dependencies=(finding.artifact_id,),
        criteria=(
            "New exact evidence establishes compatible entity, scope, quantity, modality, negation, and qualifiers.",
        ),
        status=AnswerRequirementStatus.UNRESOLVED,
        query_text=f'{question} exact entity scope qualifier evidence for "{statement}"',
        evidence_ids=(verification_claim_id,),
        source_gap_ids=gaps,
    )


def _requirement(
    *,
    kind: AnswerRequirementKind,
    description: str,
    priority: int,
    material: bool,
    target_claim_ids: tuple[str, ...],
    dependencies: tuple[str, ...],
    criteria: tuple[str, ...],
    status: AnswerRequirementStatus,
    query_text: str | None,
    evidence_ids: tuple[str, ...],
    source_gap_ids: tuple[str, ...],
) -> PlannedAnswerRequirement:
    normalized_description = " ".join(description.split())
    normalized_query = None if query_text is None else " ".join(query_text.split())
    normalized_criteria = tuple(" ".join(item.split()) for item in criteria)
    ordered_targets = tuple(dict.fromkeys(target_claim_ids))
    ordered_dependencies = tuple(dict.fromkeys(dependencies))
    ordered_evidence = tuple(dict.fromkeys(evidence_ids))
    ordered_gaps = tuple(dict.fromkeys(source_gap_ids))
    payload = {
        "schema_version": "bijux.canon.reason.answer_requirement.v1",
        "kind": kind.value,
        "description": normalized_description,
        "priority": priority,
        "material": material,
        "target_claim_artifact_ids": ordered_targets,
        "dependency_requirement_artifact_ids": ordered_dependencies,
        "satisfaction_criteria": normalized_criteria,
        "status": status.value,
        "query_text": normalized_query,
        "evidence_artifact_ids": ordered_evidence,
        "source_gap_artifact_ids": ordered_gaps,
    }
    return PlannedAnswerRequirement(
        artifact_id=content_artifact_id(payload),
        kind=kind,
        description=normalized_description,
        priority=priority,
        material=material,
        target_claim_artifact_ids=ordered_targets,
        dependency_requirement_artifact_ids=ordered_dependencies,
        satisfaction_criteria=normalized_criteria,
        status=status,
        query_text=normalized_query,
        evidence_artifact_ids=ordered_evidence,
        source_gap_artifact_ids=ordered_gaps,
    )


__all__ = [
    "AnswerRequirementKind",
    "AnswerRequirementPlan",
    "AnswerRequirementPlanOutcome",
    "AnswerRequirementPlanningService",
    "AnswerRequirementStatus",
    "PlannedAnswerRequirement",
    "SkepticalSearchCompletion",
    "create_skeptical_search_completion",
]
