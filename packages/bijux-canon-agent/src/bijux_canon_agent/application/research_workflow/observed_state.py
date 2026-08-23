"""Content-addressed state and guards for installed research decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json


def _artifact_id(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _require_artifact_id(value: str, field: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be a SHA-256 artifact ID")


class ObservedEvidenceRelationKind(StrEnum):
    """Conservative relation between one claim and one exact evidence item."""

    SUPPORT = "support"
    OPPOSITION = "opposition"
    AMBIGUITY = "ambiguity"
    IRRELEVANCE = "irrelevance"
    INSUFFICIENCY = "insufficiency"
    UNCLASSIFIED = "unclassified"


class ObservedResearchGapKind(StrEnum):
    """Stable reasons a research answer is not yet complete."""

    UNSATISFIED_REQUIREMENT = "unsatisfied_requirement"
    MATERIAL_OPPOSITION = "material_opposition"
    AMBIGUOUS_EVIDENCE = "ambiguous_evidence"
    UNCLASSIFIED_EVIDENCE = "unclassified_evidence"
    NO_RESULTS = "no_results"
    RETRIEVAL_REFUSED = "retrieval_refused"
    UNSEARCHED_IMPORTANT_CLAIM = "unsearched_important_claim"
    TOOL_FAILURE = "tool_failure"


@dataclass(frozen=True, slots=True)
class InstalledResearchRequirement:
    """One explicit answer requirement and its current satisfaction status."""

    artifact_id: str
    description: str
    claim_artifact_id: str
    satisfied: bool

    def __post_init__(self) -> None:
        _require_artifact_id(self.claim_artifact_id, "requirement claim artifact_id")
        if not self.description or self.description != " ".join(
            self.description.split()
        ):
            raise ValueError("research requirement description is not normalized")
        expected = _artifact_id(
            {
                "claim_artifact_id": self.claim_artifact_id,
                "description": self.description,
                "satisfied": self.satisfied,
            }
        )
        if self.artifact_id != expected:
            raise ValueError("research requirement identity does not match")

    @classmethod
    def create(
        cls,
        *,
        description: str,
        claim_artifact_id: str,
        satisfied: bool,
    ) -> InstalledResearchRequirement:
        normalized = " ".join(description.split())
        _require_artifact_id(claim_artifact_id, "requirement claim artifact_id")
        if not normalized:
            raise ValueError("research requirement description must not be empty")
        payload = {
            "claim_artifact_id": claim_artifact_id,
            "description": normalized,
            "satisfied": satisfied,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            description=normalized,
            claim_artifact_id=claim_artifact_id,
            satisfied=satisfied,
        )


@dataclass(frozen=True, slots=True)
class InstalledEvidenceRelation:
    """One exact observed evidence relation retained in Agent state."""

    artifact_id: str
    claim_artifact_id: str
    evidence_artifact_id: str
    kind: ObservedEvidenceRelationKind
    material: bool

    def __post_init__(self) -> None:
        _require_artifact_id(self.claim_artifact_id, "relation claim artifact_id")
        _require_artifact_id(self.evidence_artifact_id, "relation evidence artifact_id")
        expected = _artifact_id(
            {
                "claim_artifact_id": self.claim_artifact_id,
                "evidence_artifact_id": self.evidence_artifact_id,
                "kind": self.kind.value,
                "material": self.material,
            }
        )
        if self.artifact_id != expected:
            raise ValueError("evidence relation identity does not match")

    @classmethod
    def create(
        cls,
        *,
        claim_artifact_id: str,
        evidence_artifact_id: str,
        kind: ObservedEvidenceRelationKind,
        material: bool,
    ) -> InstalledEvidenceRelation:
        _require_artifact_id(claim_artifact_id, "relation claim artifact_id")
        _require_artifact_id(evidence_artifact_id, "relation evidence artifact_id")
        payload = {
            "claim_artifact_id": claim_artifact_id,
            "evidence_artifact_id": evidence_artifact_id,
            "kind": kind.value,
            "material": material,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            claim_artifact_id=claim_artifact_id,
            evidence_artifact_id=evidence_artifact_id,
            kind=kind,
            material=material,
        )


@dataclass(frozen=True, slots=True)
class ObservedResearchGap:
    """One content-addressed unresolved need consumed by transition guards."""

    artifact_id: str
    kind: ObservedResearchGapKind
    subject_artifact_id: str
    blocking: bool

    def __post_init__(self) -> None:
        _require_artifact_id(self.subject_artifact_id, "gap subject artifact_id")
        expected = _artifact_id(
            {
                "blocking": self.blocking,
                "kind": self.kind.value,
                "subject_artifact_id": self.subject_artifact_id,
            }
        )
        if self.artifact_id != expected:
            raise ValueError("research gap identity does not match")

    @classmethod
    def create(
        cls,
        *,
        kind: ObservedResearchGapKind,
        subject_artifact_id: str,
        blocking: bool = True,
    ) -> ObservedResearchGap:
        _require_artifact_id(subject_artifact_id, "gap subject artifact_id")
        payload = {
            "blocking": blocking,
            "kind": kind.value,
            "subject_artifact_id": subject_artifact_id,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            kind=kind,
            subject_artifact_id=subject_artifact_id,
            blocking=blocking,
        )


@dataclass(frozen=True, slots=True)
class ObservedResearchDecision:
    """A next action selected from exact state and observation identities."""

    artifact_id: str
    role: str
    operation: str
    rationale: str
    cause_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.role or not self.operation or not self.rationale:
            raise ValueError("research decisions require role, operation, and rationale")
        if self.rationale != " ".join(self.rationale.split()):
            raise ValueError("research decision rationale is not normalized")
        if not self.cause_artifact_ids:
            raise ValueError("research decisions require observed causes")
        for artifact_id in self.cause_artifact_ids:
            _require_artifact_id(artifact_id, "decision cause artifact_id")
        expected = _artifact_id(
            {
                "cause_artifact_ids": list(self.cause_artifact_ids),
                "operation": self.operation,
                "rationale": self.rationale,
                "role": self.role,
            }
        )
        if self.artifact_id != expected:
            raise ValueError("research decision identity does not match")

    @classmethod
    def create(
        cls,
        *,
        role: str,
        operation: str,
        rationale: str,
        cause_artifact_ids: tuple[str, ...],
    ) -> ObservedResearchDecision:
        normalized_rationale = " ".join(rationale.split())
        if not role or not operation or not normalized_rationale:
            raise ValueError("research decisions require role, operation, and rationale")
        if not cause_artifact_ids:
            raise ValueError("research decisions require observed causes")
        for artifact_id in cause_artifact_ids:
            _require_artifact_id(artifact_id, "decision cause artifact_id")
        payload = {
            "cause_artifact_ids": list(cause_artifact_ids),
            "operation": operation,
            "rationale": normalized_rationale,
            "role": role,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            role=role,
            operation=operation,
            rationale=normalized_rationale,
            cause_artifact_ids=cause_artifact_ids,
        )


@dataclass(frozen=True, slots=True)
class ObservedResearchState:
    """Complete immutable state used to select installed research actions."""

    artifact_id: str
    question: str
    requirement_artifact_ids: tuple[str, ...]
    claim_artifact_ids: tuple[str, ...]
    evidence_relations: tuple[InstalledEvidenceRelation, ...]
    gaps: tuple[ObservedResearchGap, ...]
    search_budget_limit: int
    search_budget_used: int
    decisions: tuple[ObservedResearchDecision, ...]
    terminal_status: str | None

    def __post_init__(self) -> None:
        if not self.question or self.question != " ".join(self.question.split()):
            raise ValueError("observed research question is not normalized")
        if not 0 <= self.search_budget_used <= self.search_budget_limit:
            raise ValueError("observed research search budget is invalid")
        if self.terminal_status not in {None, "completed", "incomplete", "insufficient"}:
            raise ValueError("observed research terminal status is invalid")
        identity_groups = (
            self.requirement_artifact_ids,
            self.claim_artifact_ids,
            tuple(item.artifact_id for item in self.evidence_relations),
            tuple(item.artifact_id for item in self.gaps),
            tuple(item.artifact_id for item in self.decisions),
        )
        if any(len(items) != len(set(items)) for items in identity_groups):
            raise ValueError("observed research state identities must be unique")
        for artifact_id in self.requirement_artifact_ids + self.claim_artifact_ids:
            _require_artifact_id(artifact_id, "observed research state artifact_id")
        expected = _artifact_id(
            {
                "claim_artifact_ids": list(self.claim_artifact_ids),
                "decision_artifact_ids": [
                    item.artifact_id for item in self.decisions
                ],
                "evidence_relation_artifact_ids": [
                    item.artifact_id for item in self.evidence_relations
                ],
                "gap_artifact_ids": [item.artifact_id for item in self.gaps],
                "question": self.question,
                "requirement_artifact_ids": list(self.requirement_artifact_ids),
                "search_budget_limit": self.search_budget_limit,
                "search_budget_used": self.search_budget_used,
                "terminal_status": self.terminal_status,
            }
        )
        if self.artifact_id != expected:
            raise ValueError("observed research state identity does not match")

    @property
    def blocking_gaps(self) -> tuple[ObservedResearchGap, ...]:
        """Return unresolved gaps that prevent a completed answer."""
        return tuple(gap for gap in self.gaps if gap.blocking)

    def to_record(self) -> dict[str, object]:
        """Return canonical JSON-compatible state for durable inspection."""
        return {
            "artifact_id": self.artifact_id,
            "claim_artifact_ids": list(self.claim_artifact_ids),
            "decisions": [
                {
                    "artifact_id": decision.artifact_id,
                    "cause_artifact_ids": list(decision.cause_artifact_ids),
                    "operation": decision.operation,
                    "rationale": decision.rationale,
                    "role": decision.role,
                }
                for decision in self.decisions
            ],
            "evidence_relations": [
                {
                    "artifact_id": relation.artifact_id,
                    "claim_artifact_id": relation.claim_artifact_id,
                    "evidence_artifact_id": relation.evidence_artifact_id,
                    "kind": relation.kind.value,
                    "material": relation.material,
                }
                for relation in self.evidence_relations
            ],
            "gaps": [
                {
                    "artifact_id": gap.artifact_id,
                    "blocking": gap.blocking,
                    "kind": gap.kind.value,
                    "subject_artifact_id": gap.subject_artifact_id,
                }
                for gap in self.gaps
            ],
            "question": self.question,
            "requirement_artifact_ids": list(self.requirement_artifact_ids),
            "search_budget": {
                "limit": self.search_budget_limit,
                "used": self.search_budget_used,
            },
            "terminal_status": self.terminal_status,
        }


class ObservedResearchStateMachine:
    """Build state transitions only when their declared observations permit them."""

    @classmethod
    def initial(
        cls,
        *,
        question: str,
        requirements: tuple[InstalledResearchRequirement, ...],
        claim_artifact_ids: tuple[str, ...],
        evidence_relations: tuple[InstalledEvidenceRelation, ...],
        search_budget_limit: int,
    ) -> ObservedResearchState:
        normalized_question = " ".join(question.split())
        if not normalized_question:
            raise ValueError("observed research state requires a question")
        if search_budget_limit < 0:
            raise ValueError("search budget limit must not be negative")
        for artifact_id in claim_artifact_ids:
            _require_artifact_id(artifact_id, "state claim artifact_id")
        gaps = [
            ObservedResearchGap.create(
                kind=ObservedResearchGapKind.UNSATISFIED_REQUIREMENT,
                subject_artifact_id=requirement.artifact_id,
            )
            for requirement in requirements
            if not requirement.satisfied
        ]
        for relation in evidence_relations:
            kind = {
                ObservedEvidenceRelationKind.OPPOSITION: (
                    ObservedResearchGapKind.MATERIAL_OPPOSITION
                ),
                ObservedEvidenceRelationKind.AMBIGUITY: (
                    ObservedResearchGapKind.AMBIGUOUS_EVIDENCE
                ),
                ObservedEvidenceRelationKind.INSUFFICIENCY: (
                    ObservedResearchGapKind.UNSATISFIED_REQUIREMENT
                ),
            }.get(relation.kind)
            if relation.material and kind is not None:
                gaps.append(
                    ObservedResearchGap.create(
                        kind=kind,
                        subject_artifact_id=relation.artifact_id,
                    )
                )
        return cls._create(
            question=normalized_question,
            requirement_artifact_ids=tuple(item.artifact_id for item in requirements),
            claim_artifact_ids=claim_artifact_ids,
            evidence_relations=evidence_relations,
            gaps=tuple(gaps),
            search_budget_limit=search_budget_limit,
            search_budget_used=0,
            decisions=(),
            terminal_status=None,
        )

    @classmethod
    def transition(
        cls,
        state: ObservedResearchState,
        decision: ObservedResearchDecision,
        *,
        evidence_relations: tuple[InstalledEvidenceRelation, ...] | None = None,
        gaps: tuple[ObservedResearchGap, ...] | None = None,
        consume_search: bool = False,
        terminal_status: str | None = None,
    ) -> ObservedResearchState:
        """Apply a guarded decision and retain the resulting immutable state."""
        observable_ids = {
            state.artifact_id,
            *state.requirement_artifact_ids,
            *state.claim_artifact_ids,
            *(item.artifact_id for item in state.evidence_relations),
            *(item.artifact_id for item in state.gaps),
        }
        if not observable_ids.intersection(decision.cause_artifact_ids):
            raise ValueError("research decision is not caused by the observed state")
        search_budget_used = state.search_budget_used + int(consume_search)
        if search_budget_used > state.search_budget_limit:
            raise ValueError("research transition exceeds the search budget")
        if state.terminal_status is not None:
            raise ValueError("terminal observed research state cannot transition")
        return cls._create(
            question=state.question,
            requirement_artifact_ids=state.requirement_artifact_ids,
            claim_artifact_ids=state.claim_artifact_ids,
            evidence_relations=(
                state.evidence_relations
                if evidence_relations is None
                else evidence_relations
            ),
            gaps=state.gaps if gaps is None else gaps,
            search_budget_limit=state.search_budget_limit,
            search_budget_used=search_budget_used,
            decisions=state.decisions + (decision,),
            terminal_status=terminal_status,
        )

    @staticmethod
    def _create(
        *,
        question: str,
        requirement_artifact_ids: tuple[str, ...],
        claim_artifact_ids: tuple[str, ...],
        evidence_relations: tuple[InstalledEvidenceRelation, ...],
        gaps: tuple[ObservedResearchGap, ...],
        search_budget_limit: int,
        search_budget_used: int,
        decisions: tuple[ObservedResearchDecision, ...],
        terminal_status: str | None,
    ) -> ObservedResearchState:
        payload = {
            "claim_artifact_ids": list(claim_artifact_ids),
            "decision_artifact_ids": [item.artifact_id for item in decisions],
            "evidence_relation_artifact_ids": [
                item.artifact_id for item in evidence_relations
            ],
            "gap_artifact_ids": [item.artifact_id for item in gaps],
            "question": question,
            "requirement_artifact_ids": list(requirement_artifact_ids),
            "search_budget_limit": search_budget_limit,
            "search_budget_used": search_budget_used,
            "terminal_status": terminal_status,
        }
        return ObservedResearchState(
            artifact_id=_artifact_id(payload),
            question=question,
            requirement_artifact_ids=requirement_artifact_ids,
            claim_artifact_ids=claim_artifact_ids,
            evidence_relations=evidence_relations,
            gaps=gaps,
            search_budget_limit=search_budget_limit,
            search_budget_used=search_budget_used,
            decisions=decisions,
            terminal_status=terminal_status,
        )


__all__ = [
    "InstalledEvidenceRelation",
    "InstalledResearchRequirement",
    "ObservedEvidenceRelationKind",
    "ObservedResearchDecision",
    "ObservedResearchGap",
    "ObservedResearchGapKind",
    "ObservedResearchState",
    "ObservedResearchStateMachine",
]
