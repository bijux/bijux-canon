"""Plan bounded requirement-specific searches from observed research outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import re
import unicodedata

from bijux_canon_agent.application.research_workflow.observed_state import (
    InstalledResearchRequirement,
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _artifact_id(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _require_artifact_id(value: str, field: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be a SHA-256 artifact ID")


def query_equivalence_key(value: str) -> str:
    """Return a stable key that rejects case and punctuation-only query repeats."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    tokens = re.findall(r"[\w]+", normalized, flags=re.UNICODE)
    if not tokens:
        raise ValueError("search query must contain searchable text")
    return hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()


class TargetedSearchIntent(StrEnum):
    """Evidence relationship one query is intended to establish."""

    ANSWERABILITY = "answerability"
    SUPPORT = "support"
    METHOD_CONTEXT = "method_context"
    OPPOSITION = "opposition"
    LIMITATION = "limitation"
    DISAMBIGUATION = "disambiguation"
    CROSS_CLAIM_SYNTHESIS = "cross_claim_synthesis"


class TargetedSearchTrigger(StrEnum):
    """Observed condition that justified a distinct query."""

    INITIAL_GAP = "initial_gap"
    NO_RESULTS = "no_results"
    AMBIGUOUS_RESULT = "ambiguous_result"
    OPPOSING_RESULT = "opposing_result"


class TargetedSearchOutcome(StrEnum):
    """Typed observation available to the next planning decision."""

    NO_RESULTS = "no_results"
    AMBIGUOUS = "ambiguous"
    OPPOSITION = "opposition"
    SUPPORT = "support"
    MATERIAL_CANDIDATE = "material_candidate"
    REFUSED = "refused"


class TargetedSearchDisposition(StrEnum):
    """Reason a requirement was selected or excluded from this decision."""

    SELECTED = "selected"
    SATISFIED = "satisfied"
    NON_MATERIAL = "non_material"
    NOT_SEARCHABLE = "not_searchable"
    DEPENDENCY_UNRESOLVED = "dependency_unresolved"
    AWAITING_OBSERVATION = "awaiting_observation"
    CLOSED_BY_OBSERVATION = "closed_by_observation"
    ATTEMPT_BUDGET = "attempt_budget"
    EQUIVALENT_QUERY = "equivalent_query"
    TOTAL_BUDGET = "total_budget"


@dataclass(frozen=True, slots=True)
class TargetedSearchPolicy:
    """Hard per-requirement, total-attempt, and query-size bounds."""

    max_attempts: int = 8
    max_attempts_per_requirement: int = 2
    max_query_characters: int = 4_096

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 100:
            raise ValueError("targeted search attempt budget must be within 1..100")
        if not 1 <= self.max_attempts_per_requirement <= 8:
            raise ValueError(
                "targeted search per-requirement budget must be within 1..8"
            )
        if not 64 <= self.max_query_characters <= 100_000:
            raise ValueError("targeted search query bound must be within 64..100000")


@dataclass(frozen=True, slots=True)
class TargetedSearchAttempt:
    """One content-addressed call targeting one exact unresolved requirement."""

    artifact_id: str
    requirement_artifact_id: str
    source_requirement_artifact_id: str | None
    target_claim_artifact_ids: tuple[str, ...]
    intent: TargetedSearchIntent
    trigger: TargetedSearchTrigger
    ordinal_for_requirement: int
    query_text: str
    query_equivalence_sha256: str
    rationale: str
    satisfaction_criteria: tuple[str, ...]
    prior_attempt_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.artifact_id, "targeted search artifact_id"),
            (self.requirement_artifact_id, "targeted search requirement"),
        ):
            _require_artifact_id(value, field)
        if self.source_requirement_artifact_id is not None:
            _require_artifact_id(
                self.source_requirement_artifact_id,
                "source answer requirement",
            )
        for artifact_id in (
            self.target_claim_artifact_ids + self.prior_attempt_artifact_ids
        ):
            _require_artifact_id(artifact_id, "targeted search reference")
        if self.ordinal_for_requirement <= 0:
            raise ValueError("targeted search ordinal must be positive")
        if self.query_text != " ".join(self.query_text.split()):
            raise ValueError("targeted search query must be normalized")
        if query_equivalence_key(self.query_text) != self.query_equivalence_sha256:
            raise ValueError("targeted search query equivalence identity differs")
        if not self.rationale or not self.satisfaction_criteria:
            raise ValueError(
                "targeted search needs rationale and satisfaction criteria"
            )
        expected = _artifact_id(asdict(self) | {"artifact_id": None})
        if self.artifact_id != expected:
            raise ValueError("targeted search attempt identity does not match")


@dataclass(frozen=True, slots=True)
class TargetedSearchObservation:
    """Typed material result bound to one exact attempted query."""

    artifact_id: str
    attempt_artifact_id: str
    outcome: TargetedSearchOutcome
    evidence_artifact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "search observation artifact_id")
        _require_artifact_id(self.attempt_artifact_id, "observed search attempt")
        for artifact_id in self.evidence_artifact_ids:
            _require_artifact_id(artifact_id, "observed search evidence")
        if len(self.evidence_artifact_ids) != len(set(self.evidence_artifact_ids)):
            raise ValueError("search observation evidence identities must be unique")
        evidence_required = self.outcome in {
            TargetedSearchOutcome.OPPOSITION,
            TargetedSearchOutcome.SUPPORT,
            TargetedSearchOutcome.MATERIAL_CANDIDATE,
        }
        if evidence_required != bool(self.evidence_artifact_ids):
            raise ValueError("search observation outcome and evidence differ")
        expected = _artifact_id(asdict(self) | {"artifact_id": None})
        if self.artifact_id != expected:
            raise ValueError("targeted search observation identity does not match")

    @classmethod
    def create(
        cls,
        *,
        attempt_artifact_id: str,
        outcome: TargetedSearchOutcome,
        evidence_artifact_ids: tuple[str, ...] = (),
    ) -> TargetedSearchObservation:
        payload = {
            "artifact_id": None,
            "attempt_artifact_id": attempt_artifact_id,
            "outcome": outcome,
            "evidence_artifact_ids": evidence_artifact_ids,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            attempt_artifact_id=attempt_artifact_id,
            outcome=outcome,
            evidence_artifact_ids=evidence_artifact_ids,
        )


@dataclass(frozen=True, slots=True)
class TargetedSearchDecision:
    """Inspectable selection or exclusion for one answer requirement."""

    requirement_artifact_id: str
    disposition: TargetedSearchDisposition
    rationale: str
    attempt_artifact_id: str | None

    def __post_init__(self) -> None:
        _require_artifact_id(
            self.requirement_artifact_id, "search decision requirement"
        )
        if self.attempt_artifact_id is not None:
            _require_artifact_id(self.attempt_artifact_id, "search decision attempt")
        if not self.rationale:
            raise ValueError("targeted search decisions require a rationale")
        if (self.disposition is TargetedSearchDisposition.SELECTED) != (
            self.attempt_artifact_id is not None
        ):
            raise ValueError("only selected decisions may bind an attempt")


@dataclass(frozen=True, slots=True)
class TargetedSearchPlan:
    """One deterministic next-call decision over all current evidence needs."""

    schema_version: str
    artifact_id: str
    policy_artifact_id: str
    attempt: TargetedSearchAttempt | None
    decisions: tuple[TargetedSearchDecision, ...]

    def __post_init__(self) -> None:
        _require_artifact_id(self.artifact_id, "targeted search plan artifact_id")
        _require_artifact_id(self.policy_artifact_id, "targeted search policy")
        selected = tuple(
            item
            for item in self.decisions
            if item.disposition is TargetedSearchDisposition.SELECTED
        )
        if len(selected) != int(self.attempt is not None):
            raise ValueError("targeted search plan must select at most one attempt")
        if self.attempt is not None and (
            selected[0].attempt_artifact_id != self.attempt.artifact_id
        ):
            raise ValueError("targeted search decision and attempt differ")
        expected = _artifact_id(asdict(self) | {"artifact_id": None})
        if self.artifact_id != expected:
            raise ValueError("targeted search plan identity does not match")


class TargetedSearchPlanningService:
    """Choose the next distinct query from requirements and observed outcomes."""

    def __init__(self, policy: TargetedSearchPolicy | None = None) -> None:
        self.policy = policy or TargetedSearchPolicy()

    def plan(
        self,
        requirements: tuple[InstalledResearchRequirement, ...],
        *,
        attempts: tuple[TargetedSearchAttempt, ...] = (),
        observations: tuple[TargetedSearchObservation, ...] = (),
    ) -> TargetedSearchPlan:
        """Return exactly one justified next attempt, or an explained stop plan."""

        requirement_ids = tuple(item.artifact_id for item in requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("targeted search requirements must be unique")
        attempt_ids = tuple(item.artifact_id for item in attempts)
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("targeted search attempts must be unique")
        current_source_ids = {
            item.source_requirement_artifact_id
            for item in requirements
            if item.source_requirement_artifact_id is not None
        }
        if any(
            item.requirement_artifact_id not in requirement_ids
            and item.source_requirement_artifact_id not in current_source_ids
            for item in attempts
        ):
            raise ValueError(
                "targeted search attempt references an unknown requirement"
            )
        by_attempt = {item.artifact_id: item for item in attempts}
        observed: dict[str, TargetedSearchObservation] = {}
        for observation in observations:
            if observation.attempt_artifact_id not in by_attempt:
                raise ValueError("search observation references an unknown attempt")
            if observation.attempt_artifact_id in observed:
                raise ValueError("one search attempt cannot have multiple observations")
            observed[observation.attempt_artifact_id] = observation

        policy_id = _artifact_id(asdict(self.policy))
        ordered = sorted(
            requirements, key=lambda item: (-item.priority, item.artifact_id)
        )
        if len(attempts) >= self.policy.max_attempts:
            budget_decisions = tuple(
                TargetedSearchDecision(
                    item.artifact_id,
                    TargetedSearchDisposition.TOTAL_BUDGET,
                    "the total targeted-search attempt budget is exhausted",
                    None,
                )
                for item in ordered
            )
            return _plan(policy_id, None, budget_decisions)

        known_equivalence = {item.query_equivalence_sha256 for item in attempts}
        decisions: list[TargetedSearchDecision] = []
        selected: TargetedSearchAttempt | None = None
        for requirement in ordered:
            disposition, rationale, proposal = self._proposal(
                requirement,
                requirements=requirements,
                attempts=attempts,
                observed=observed,
            )
            if proposal is not None:
                if proposal.query_equivalence_sha256 in known_equivalence:
                    disposition = TargetedSearchDisposition.EQUIVALENT_QUERY
                    rationale = "the proposed query is equivalent to a prior attempt and cannot run"
                    proposal = None
                elif selected is None:
                    selected = proposal
                    known_equivalence.add(proposal.query_equivalence_sha256)
                else:
                    disposition = TargetedSearchDisposition.TOTAL_BUDGET
                    rationale = (
                        "another higher-priority requirement owns this next call"
                    )
                    proposal = None
            decisions.append(
                TargetedSearchDecision(
                    requirement.artifact_id,
                    disposition,
                    rationale,
                    None if proposal is None else proposal.artifact_id,
                )
            )
        return _plan(policy_id, selected, tuple(decisions))

    def _proposal(
        self,
        requirement: InstalledResearchRequirement,
        *,
        requirements: tuple[InstalledResearchRequirement, ...],
        attempts: tuple[TargetedSearchAttempt, ...],
        observed: dict[str, TargetedSearchObservation],
    ) -> tuple[TargetedSearchDisposition, str, TargetedSearchAttempt | None]:
        if requirement.satisfied:
            return TargetedSearchDisposition.SATISFIED, "requirement is satisfied", None
        if not requirement.material:
            return (
                TargetedSearchDisposition.NON_MATERIAL,
                "requirement is non-material",
                None,
            )
        if requirement.status != "unresolved" or requirement.query_text is None:
            return (
                TargetedSearchDisposition.NOT_SEARCHABLE,
                "requirement has no policy-admitted search query",
                None,
            )
        by_source = {
            item.source_requirement_artifact_id: item
            for item in requirements
            if item.source_requirement_artifact_id is not None
        }
        if any(
            dependency not in by_source or not by_source[dependency].satisfied
            for dependency in requirement.dependency_requirement_artifact_ids
        ):
            return (
                TargetedSearchDisposition.DEPENDENCY_UNRESOLVED,
                "a prerequisite answer requirement remains unresolved",
                None,
            )
        prior = tuple(
            item
            for item in attempts
            if item.requirement_artifact_id == requirement.artifact_id
            or (
                requirement.source_requirement_artifact_id is not None
                and item.source_requirement_artifact_id
                == requirement.source_requirement_artifact_id
            )
        )
        if len(prior) >= self.policy.max_attempts_per_requirement:
            return (
                TargetedSearchDisposition.ATTEMPT_BUDGET,
                "the per-requirement search attempt budget is exhausted",
                None,
            )
        trigger = TargetedSearchTrigger.INITIAL_GAP
        if prior:
            latest = prior[-1]
            observation = observed.get(latest.artifact_id)
            if observation is None:
                return (
                    TargetedSearchDisposition.AWAITING_OBSERVATION,
                    "the prior query has no recorded outcome",
                    None,
                )
            trigger = {
                TargetedSearchOutcome.NO_RESULTS: TargetedSearchTrigger.NO_RESULTS,
                TargetedSearchOutcome.AMBIGUOUS: TargetedSearchTrigger.AMBIGUOUS_RESULT,
                TargetedSearchOutcome.OPPOSITION: TargetedSearchTrigger.OPPOSING_RESULT,
            }.get(observation.outcome, TargetedSearchTrigger.INITIAL_GAP)
            if observation.outcome in {
                TargetedSearchOutcome.SUPPORT,
                TargetedSearchOutcome.MATERIAL_CANDIDATE,
                TargetedSearchOutcome.REFUSED,
            }:
                return (
                    TargetedSearchDisposition.CLOSED_BY_OBSERVATION,
                    "the observed result requires satisfaction, classification, or refusal handling before another query",
                    None,
                )
        attempt = _attempt(requirement, prior=prior, trigger=trigger)
        if len(attempt.query_text) > self.policy.max_query_characters:
            return (
                TargetedSearchDisposition.NOT_SEARCHABLE,
                "the targeted query exceeds the configured character bound",
                None,
            )
        return (
            TargetedSearchDisposition.SELECTED,
            "highest-priority unresolved requirement with a distinct policy-admitted query",
            attempt,
        )


def _intent(kind: str) -> TargetedSearchIntent:
    return {
        "answerability": TargetedSearchIntent.ANSWERABILITY,
        "finding": TargetedSearchIntent.SUPPORT,
        "method_context": TargetedSearchIntent.METHOD_CONTEXT,
        "opposition": TargetedSearchIntent.OPPOSITION,
        "limitation": TargetedSearchIntent.LIMITATION,
        "disambiguation": TargetedSearchIntent.DISAMBIGUATION,
        "cross_claim_synthesis": TargetedSearchIntent.CROSS_CLAIM_SYNTHESIS,
    }.get(kind, TargetedSearchIntent.SUPPORT)


def _attempt(
    requirement: InstalledResearchRequirement,
    *,
    prior: tuple[TargetedSearchAttempt, ...],
    trigger: TargetedSearchTrigger,
) -> TargetedSearchAttempt:
    assert requirement.query_text is not None
    intent = _intent(requirement.kind)
    suffix = {
        TargetedSearchTrigger.INITIAL_GAP: {
            TargetedSearchIntent.ANSWERABILITY: "direct answer evidence corpus scope",
            TargetedSearchIntent.SUPPORT: "direct support exact entity scope context",
            TargetedSearchIntent.METHOD_CONTEXT: "methods sampling protocol analysis context",
            TargetedSearchIntent.OPPOSITION: "contradictory evidence null result boundary condition",
            TargetedSearchIntent.LIMITATION: "limitations sample scope uncertainty context",
            TargetedSearchIntent.DISAMBIGUATION: "exact entity geography time quantity modality negation",
            TargetedSearchIntent.CROSS_CLAIM_SYNTHESIS: "relationship compatible scope across findings",
        }[intent],
        TargetedSearchTrigger.NO_RESULTS: (
            "alternative terminology related population broader context negative result"
        ),
        TargetedSearchTrigger.AMBIGUOUS_RESULT: (
            "exact entity population geography time quantity qualifier modality negation"
        ),
        TargetedSearchTrigger.OPPOSING_RESULT: (
            "replication boundary conditions reconcile disagreement supporting evidence"
        ),
    }[trigger]
    query = " ".join(f"{requirement.query_text} {suffix}".split())
    payload = {
        "artifact_id": None,
        "requirement_artifact_id": requirement.artifact_id,
        "source_requirement_artifact_id": requirement.source_requirement_artifact_id,
        "target_claim_artifact_ids": requirement.target_claim_artifact_ids,
        "intent": intent,
        "trigger": trigger,
        "ordinal_for_requirement": len(prior) + 1,
        "query_text": query,
        "query_equivalence_sha256": query_equivalence_key(query),
        "rationale": (
            f"Target the {requirement.kind} requirement because: "
            + "; ".join(requirement.satisfaction_criteria)
        ),
        "satisfaction_criteria": requirement.satisfaction_criteria,
        "prior_attempt_artifact_ids": tuple(item.artifact_id for item in prior),
    }
    return TargetedSearchAttempt(
        artifact_id=_artifact_id(payload),
        requirement_artifact_id=requirement.artifact_id,
        source_requirement_artifact_id=requirement.source_requirement_artifact_id,
        target_claim_artifact_ids=requirement.target_claim_artifact_ids,
        intent=intent,
        trigger=trigger,
        ordinal_for_requirement=len(prior) + 1,
        query_text=query,
        query_equivalence_sha256=query_equivalence_key(query),
        rationale=(
            f"Target the {requirement.kind} requirement because: "
            + "; ".join(requirement.satisfaction_criteria)
        ),
        satisfaction_criteria=requirement.satisfaction_criteria,
        prior_attempt_artifact_ids=tuple(item.artifact_id for item in prior),
    )


def _plan(
    policy_id: str,
    attempt: TargetedSearchAttempt | None,
    decisions: tuple[TargetedSearchDecision, ...],
) -> TargetedSearchPlan:
    schema_version = "bijux.canon.agent.targeted_search_plan.v1"
    payload = {
        "schema_version": schema_version,
        "artifact_id": None,
        "policy_artifact_id": policy_id,
        "attempt": None if attempt is None else asdict(attempt),
        "decisions": tuple(asdict(item) for item in decisions),
    }
    return TargetedSearchPlan(
        schema_version=schema_version,
        artifact_id=_artifact_id(payload),
        policy_artifact_id=policy_id,
        attempt=attempt,
        decisions=decisions,
    )


__all__ = [
    "TargetedSearchAttempt",
    "TargetedSearchDecision",
    "TargetedSearchDisposition",
    "TargetedSearchIntent",
    "TargetedSearchObservation",
    "TargetedSearchOutcome",
    "TargetedSearchPlan",
    "TargetedSearchPlanningService",
    "TargetedSearchPolicy",
    "TargetedSearchTrigger",
    "query_equivalence_key",
]
