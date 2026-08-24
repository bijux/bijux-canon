# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Compute deterministic terminal decisions for bounded research cycles."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class ConvergenceReason(StrEnum):
    """Stable reason a research cycle continues or terminates."""

    coverage_and_answerability = "coverage_and_answerability"
    stable_graph = "stable_graph"
    diminishing_evidence_value = "diminishing_evidence_value"
    iteration_limit = "iteration_limit"
    tool_limit = "tool_limit"
    token_limit = "token_limit"
    time_limit = "time_limit"
    cancelled = "cancelled"
    explicit_insufficiency = "explicit_insufficiency"
    continue_research = "continue_research"


class ConvergenceOutcome(StrEnum):
    """Terminal or continuing state exposed to the research orchestrator."""

    continue_research = "continue_research"
    converged = "converged"
    insufficient = "insufficient"
    cancelled = "cancelled"
    budget_exhausted = "budget_exhausted"


class AnswerVerificationStatus(StrEnum):
    """Grounding disposition used by research convergence."""

    admitted = "admitted"
    partially_admitted = "partially_admitted"
    abstained = "abstained"
    not_run = "not_run"


class ConvergenceErrorCode(StrEnum):
    """Stable history-integrity failures before convergence evaluation."""

    empty_history = "empty_history"
    nonsequential_iteration = "nonsequential_iteration"
    cumulative_usage_regressed = "cumulative_usage_regressed"
    history_after_terminal_decision = "history_after_terminal_decision"


class ConvergenceError(ValueError):
    """Convergence cannot be computed from an invalid observation history."""

    def __init__(self, code: ConvergenceErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ConvergencePolicy(StableModel):
    """Hard resource ceilings and semantic stopping thresholds."""

    max_iterations: int = 12
    max_tool_calls: int = 100
    max_tokens: int = 100_000
    max_elapsed_ms: int = 300_000
    minimum_coverage: float = 0.8
    stable_graph_observations: int = 2
    diminishing_value_observations: int = 2
    minimum_marginal_evidence_value: float = 0.01

    @model_validator(mode="after")
    def _validate_policy(self) -> Self:
        if not 1 <= self.max_iterations <= 10_000:
            raise ValueError("iteration limit must be within 1..10000")
        if not 1 <= self.max_tool_calls <= 1_000_000:
            raise ValueError("tool-call limit must be within 1..1000000")
        if not 1 <= self.max_tokens <= 1_000_000_000:
            raise ValueError("token limit must be within 1..1000000000")
        if not 1 <= self.max_elapsed_ms <= 86_400_000:
            raise ValueError("elapsed-time limit must be within 1..86400000")
        if (
            not math.isfinite(self.minimum_coverage)
            or not 0 <= self.minimum_coverage <= 1
        ):
            raise ValueError("minimum coverage must be finite and in [0,1]")
        if not 2 <= self.stable_graph_observations <= self.max_iterations:
            raise ValueError("stable-graph window must be within 2..max_iterations")
        if not 2 <= self.diminishing_value_observations <= self.max_iterations:
            raise ValueError(
                "diminishing-value window must be within 2..max_iterations"
            )
        if (
            not math.isfinite(self.minimum_marginal_evidence_value)
            or not 0 <= self.minimum_marginal_evidence_value <= 1
        ):
            raise ValueError("marginal evidence floor must be finite and in [0,1]")
        return self


class ConvergenceObservation(StableModel):
    """Immutable graph quality and cumulative resource state after one iteration."""

    artifact_id: str
    iteration: int
    graph_artifact_id: str
    coverage: float
    verified_answerable_claims: int
    required_claims: int
    blocking_gap_count: int
    new_evidence_count: int
    marginal_evidence_value: float
    cumulative_tool_calls: int
    cumulative_tokens: int
    cumulative_elapsed_ms: int
    cancellation_requested: bool
    explicit_insufficiency: bool

    @field_validator("artifact_id", "graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_observation(self) -> Self:
        if self.iteration <= 0:
            raise ValueError("convergence iteration must be positive")
        if not math.isfinite(self.coverage) or not 0 <= self.coverage <= 1:
            raise ValueError("coverage must be finite and in [0,1]")
        if (
            not math.isfinite(self.marginal_evidence_value)
            or not 0 <= self.marginal_evidence_value <= 1
        ):
            raise ValueError("marginal evidence value must be finite and in [0,1]")
        counts = (
            self.verified_answerable_claims,
            self.required_claims,
            self.blocking_gap_count,
            self.new_evidence_count,
            self.cumulative_tool_calls,
            self.cumulative_tokens,
            self.cumulative_elapsed_ms,
        )
        if any(value < 0 for value in counts):
            raise ValueError("convergence counts and usage must not be negative")
        if self.verified_answerable_claims > self.required_claims:
            raise ValueError("verified answerable claims cannot exceed required claims")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("convergence observation identity does not match")
        return self


class ResearchConvergenceEvidence(StableModel):
    """Versioned semantic evidence for one terminal convergence decision."""

    schema_version: Literal["bijux.canon.reason.research_convergence_evidence.v1"] = (
        "bijux.canon.reason.research_convergence_evidence.v1"
    )
    artifact_id: str
    current_graph_artifact_id: str
    material_requirement_count: int
    satisfied_requirement_artifact_ids: tuple[str, ...]
    remaining_requirement_artifact_ids: tuple[str, ...]
    material_candidate_count: int
    classified_candidate_count: int
    unresolved_classification_artifact_ids: tuple[str, ...]
    blocking_gap_artifact_ids: tuple[str, ...]
    unsearched_important_claim_artifact_ids: tuple[str, ...]
    answer_verification_status: AnswerVerificationStatus
    answer_revision_artifact_id: str | None
    material_conflict_count: int
    marginal_evidence_values: tuple[float, ...]

    @field_validator("artifact_id", "current_graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("answer_revision_artifact_id")
    @classmethod
    def _validate_optional_artifact_id(cls, value: str | None) -> str | None:
        return None if value is None else require_artifact_id(value)

    @field_validator(
        "satisfied_requirement_artifact_ids",
        "remaining_requirement_artifact_ids",
        "unresolved_classification_artifact_ids",
        "blocking_gap_artifact_ids",
        "unsearched_important_claim_artifact_ids",
    )
    @classmethod
    def _validate_artifact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("convergence evidence identities must be unique")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_evidence(self) -> Self:
        counts = (
            self.material_requirement_count,
            self.material_candidate_count,
            self.classified_candidate_count,
            self.material_conflict_count,
        )
        if any(item < 0 for item in counts):
            raise ValueError("convergence evidence counts cannot be negative")
        if len(self.satisfied_requirement_artifact_ids) + len(
            self.remaining_requirement_artifact_ids
        ) != self.material_requirement_count or set(
            self.satisfied_requirement_artifact_ids
        ) & set(self.remaining_requirement_artifact_ids):
            raise ValueError("material requirement accounting is incomplete")
        if self.classified_candidate_count > self.material_candidate_count:
            raise ValueError("classified candidates exceed material candidates")
        if any(
            not math.isfinite(item) or not 0 <= item <= 1
            for item in self.marginal_evidence_values
        ):
            raise ValueError("marginal evidence values must be finite and bounded")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("research convergence evidence identity does not match")
        return self

    @property
    def requirement_coverage(self) -> float:
        """Return material requirement coverage without a hidden denominator."""

        if self.material_requirement_count == 0:
            return 0.0
        return (
            len(self.satisfied_requirement_artifact_ids)
            / self.material_requirement_count
        )

    @property
    def classification_complete(self) -> bool:
        """Return whether every material candidate has a resolved classification."""

        return (
            self.classified_candidate_count == self.material_candidate_count
            and not self.unresolved_classification_artifact_ids
        )

    @property
    def answerable(self) -> bool:
        """Return whether verified state permits a completed research answer."""

        return (
            self.material_requirement_count > 0
            and not self.remaining_requirement_artifact_ids
            and self.classification_complete
            and not self.blocking_gap_artifact_ids
            and not self.unsearched_important_claim_artifact_ids
            and self.answer_verification_status
            in {
                AnswerVerificationStatus.admitted,
                AnswerVerificationStatus.partially_admitted,
            }
        )


class ConvergenceDecision(StableModel):
    """Content-addressed decision that can never continue past a stop condition."""

    schema_version: Literal[
        "bijux.canon.reason.convergence_decision.v1",
        "bijux.canon.reason.convergence_decision.v2",
    ] = "bijux.canon.reason.convergence_decision.v1"
    artifact_id: str
    policy: ConvergencePolicy
    observation_artifact_ids: tuple[str, ...]
    current_graph_artifact_id: str
    outcome: ConvergenceOutcome
    stop: bool
    reasons: tuple[ConvergenceReason, ...]
    evidence: ResearchConvergenceEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @field_validator("artifact_id", "current_graph_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @field_validator("observation_artifact_ids")
    @classmethod
    def _validate_observations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(value) != len(set(value)):
            raise ValueError("convergence decisions require unique observations")
        return tuple(require_artifact_id(item) for item in value)

    @model_validator(mode="after")
    def _validate_decision(self) -> Self:
        if (self.schema_version.endswith(".v2")) != (self.evidence is not None):
            raise ValueError("convergence decision version and evidence differ")
        if tuple(sorted(set(self.reasons))) != self.reasons:
            raise ValueError("convergence reasons must be unique and sorted")
        continuing = self.outcome is ConvergenceOutcome.continue_research
        if continuing != (not self.stop):
            raise ValueError("only continue_research decisions may keep cycling")
        if continuing != (self.reasons == (ConvergenceReason.continue_research,)):
            raise ValueError("continuing requires the sole continue reason")
        if self.evidence is not None and (
            self.evidence.current_graph_artifact_id != self.current_graph_artifact_id
        ):
            raise ValueError("convergence evidence refers to another graph")
        if self.artifact_id != content_artifact_id(
            self.model_dump(mode="json", exclude={"artifact_id"})
        ):
            raise ValueError("convergence decision identity does not match")
        return self


class ConvergenceService:
    """Evaluate semantic progress and every hard bound on each iteration."""

    def __init__(self, policy: ConvergencePolicy | None = None) -> None:
        self.policy = policy or ConvergencePolicy()

    def evaluate(
        self,
        observations: tuple[ConvergenceObservation, ...],
        *,
        evidence: ResearchConvergenceEvidence | None = None,
    ) -> ConvergenceDecision:
        """Return a terminal decision whenever any declared stop condition holds."""

        if not observations:
            raise ConvergenceError(
                ConvergenceErrorCode.empty_history,
                "convergence requires at least one observation",
            )
        self._validate_history(observations)
        current = observations[-1]
        if evidence is not None:
            self._validate_evidence_binding(current, evidence)
        reasons = self._terminal_reasons(observations, evidence=evidence)
        if not reasons:
            reasons = (ConvergenceReason.continue_research,)
            outcome = ConvergenceOutcome.continue_research
            stop = False
        else:
            outcome = _outcome(reasons, current, evidence=evidence)
            stop = True
        schema_version: Literal[
            "bijux.canon.reason.convergence_decision.v1",
            "bijux.canon.reason.convergence_decision.v2",
        ] = (
            "bijux.canon.reason.convergence_decision.v1"
            if evidence is None
            else "bijux.canon.reason.convergence_decision.v2"
        )
        payload = {
            "schema_version": schema_version,
            "policy": self.policy.model_dump(mode="json"),
            "observation_artifact_ids": tuple(
                item.artifact_id for item in observations
            ),
            "current_graph_artifact_id": current.graph_artifact_id,
            "outcome": outcome.value,
            "stop": stop,
            "reasons": tuple(item.value for item in reasons),
        }
        if evidence is not None:
            payload["evidence"] = evidence.model_dump(mode="json")
        return ConvergenceDecision(
            schema_version=schema_version,
            artifact_id=content_artifact_id(payload),
            policy=self.policy,
            observation_artifact_ids=tuple(item.artifact_id for item in observations),
            current_graph_artifact_id=current.graph_artifact_id,
            outcome=outcome,
            stop=stop,
            reasons=reasons,
            evidence=evidence,
        )

    @staticmethod
    def _validate_evidence_binding(
        current: ConvergenceObservation,
        evidence: ResearchConvergenceEvidence,
    ) -> None:
        if (
            current.graph_artifact_id != evidence.current_graph_artifact_id
            or current.required_claims != evidence.material_requirement_count
            or current.verified_answerable_claims
            != len(evidence.satisfied_requirement_artifact_ids)
            or current.blocking_gap_count != len(evidence.blocking_gap_artifact_ids)
            or current.coverage != evidence.requirement_coverage
        ):
            raise ValueError("convergence observation differs from semantic evidence")

    def _validate_history(
        self, observations: tuple[ConvergenceObservation, ...]
    ) -> None:
        iterations = tuple(item.iteration for item in observations)
        if iterations != tuple(range(1, len(observations) + 1)):
            raise ConvergenceError(
                ConvergenceErrorCode.nonsequential_iteration,
                "convergence observations must begin at one and remain sequential",
            )
        for previous, current in zip(observations, observations[1:], strict=False):
            if any(
                after < before
                for before, after in (
                    (previous.cumulative_tool_calls, current.cumulative_tool_calls),
                    (previous.cumulative_tokens, current.cumulative_tokens),
                    (previous.cumulative_elapsed_ms, current.cumulative_elapsed_ms),
                )
            ):
                raise ConvergenceError(
                    ConvergenceErrorCode.cumulative_usage_regressed,
                    "cumulative research usage cannot decrease",
                )
        for end in range(1, len(observations)):
            if self._terminal_reasons(observations[:end]):
                raise ConvergenceError(
                    ConvergenceErrorCode.history_after_terminal_decision,
                    "research observations cannot continue after a terminal decision",
                )

    def _terminal_reasons(
        self,
        observations: tuple[ConvergenceObservation, ...],
        *,
        evidence: ResearchConvergenceEvidence | None = None,
    ) -> tuple[ConvergenceReason, ...]:
        current = observations[-1]
        reasons = set()
        if current.cancellation_requested:
            reasons.add(ConvergenceReason.cancelled)
        if current.explicit_insufficiency:
            reasons.add(ConvergenceReason.explicit_insufficiency)
        if current.iteration >= self.policy.max_iterations:
            reasons.add(ConvergenceReason.iteration_limit)
        if current.cumulative_tool_calls >= self.policy.max_tool_calls:
            reasons.add(ConvergenceReason.tool_limit)
        if current.cumulative_tokens >= self.policy.max_tokens:
            reasons.add(ConvergenceReason.token_limit)
        if current.cumulative_elapsed_ms >= self.policy.max_elapsed_ms:
            reasons.add(ConvergenceReason.time_limit)
        answerable = (
            evidence.answerable
            if evidence is not None
            else (
                current.required_claims > 0
                and current.verified_answerable_claims == current.required_claims
                and current.blocking_gap_count == 0
            )
        )
        if current.coverage >= self.policy.minimum_coverage and answerable:
            reasons.add(ConvergenceReason.coverage_and_answerability)
        stable_window = observations[-self.policy.stable_graph_observations :]
        if (
            len(stable_window) == self.policy.stable_graph_observations
            and len({item.graph_artifact_id for item in stable_window}) == 1
        ):
            reasons.add(ConvergenceReason.stable_graph)
        value_window = observations[-self.policy.diminishing_value_observations :]
        if len(value_window) == self.policy.diminishing_value_observations and all(
            item.marginal_evidence_value < self.policy.minimum_marginal_evidence_value
            for item in value_window
        ):
            reasons.add(ConvergenceReason.diminishing_evidence_value)
        if (
            evidence is not None
            and len(evidence.marginal_evidence_values)
            >= self.policy.diminishing_value_observations
            and all(
                item < self.policy.minimum_marginal_evidence_value
                for item in evidence.marginal_evidence_values[
                    -self.policy.diminishing_value_observations :
                ]
            )
        ):
            reasons.add(ConvergenceReason.diminishing_evidence_value)
        return tuple(sorted(reasons))


def create_research_convergence_evidence(
    *,
    current_graph_artifact_id: str,
    material_requirement_count: int,
    satisfied_requirement_artifact_ids: tuple[str, ...],
    remaining_requirement_artifact_ids: tuple[str, ...],
    material_candidate_count: int,
    classified_candidate_count: int,
    unresolved_classification_artifact_ids: tuple[str, ...],
    blocking_gap_artifact_ids: tuple[str, ...],
    unsearched_important_claim_artifact_ids: tuple[str, ...],
    answer_verification_status: AnswerVerificationStatus,
    answer_revision_artifact_id: str | None,
    material_conflict_count: int,
    marginal_evidence_values: tuple[float, ...],
) -> ResearchConvergenceEvidence:
    """Create immutable semantic convergence evidence."""

    payload = {
        "schema_version": "bijux.canon.reason.research_convergence_evidence.v1",
        "current_graph_artifact_id": current_graph_artifact_id,
        "material_requirement_count": material_requirement_count,
        "satisfied_requirement_artifact_ids": satisfied_requirement_artifact_ids,
        "remaining_requirement_artifact_ids": remaining_requirement_artifact_ids,
        "material_candidate_count": material_candidate_count,
        "classified_candidate_count": classified_candidate_count,
        "unresolved_classification_artifact_ids": unresolved_classification_artifact_ids,
        "blocking_gap_artifact_ids": blocking_gap_artifact_ids,
        "unsearched_important_claim_artifact_ids": (
            unsearched_important_claim_artifact_ids
        ),
        "answer_verification_status": answer_verification_status.value,
        "answer_revision_artifact_id": answer_revision_artifact_id,
        "material_conflict_count": material_conflict_count,
        "marginal_evidence_values": marginal_evidence_values,
    }
    return ResearchConvergenceEvidence.model_validate(
        {"artifact_id": content_artifact_id(payload), **payload}
    )


def create_convergence_observation(
    *,
    iteration: int,
    graph_artifact_id: str,
    coverage: float,
    verified_answerable_claims: int,
    required_claims: int,
    blocking_gap_count: int,
    new_evidence_count: int,
    marginal_evidence_value: float,
    cumulative_tool_calls: int,
    cumulative_tokens: int,
    cumulative_elapsed_ms: int,
    cancellation_requested: bool = False,
    explicit_insufficiency: bool = False,
) -> ConvergenceObservation:
    """Create one immutable post-iteration convergence observation."""

    payload = {
        "iteration": iteration,
        "graph_artifact_id": graph_artifact_id,
        "coverage": float(coverage),
        "verified_answerable_claims": verified_answerable_claims,
        "required_claims": required_claims,
        "blocking_gap_count": blocking_gap_count,
        "new_evidence_count": new_evidence_count,
        "marginal_evidence_value": float(marginal_evidence_value),
        "cumulative_tool_calls": cumulative_tool_calls,
        "cumulative_tokens": cumulative_tokens,
        "cumulative_elapsed_ms": cumulative_elapsed_ms,
        "cancellation_requested": cancellation_requested,
        "explicit_insufficiency": explicit_insufficiency,
    }
    return ConvergenceObservation(
        artifact_id=content_artifact_id(payload),
        iteration=iteration,
        graph_artifact_id=graph_artifact_id,
        coverage=coverage,
        verified_answerable_claims=verified_answerable_claims,
        required_claims=required_claims,
        blocking_gap_count=blocking_gap_count,
        new_evidence_count=new_evidence_count,
        marginal_evidence_value=marginal_evidence_value,
        cumulative_tool_calls=cumulative_tool_calls,
        cumulative_tokens=cumulative_tokens,
        cumulative_elapsed_ms=cumulative_elapsed_ms,
        cancellation_requested=cancellation_requested,
        explicit_insufficiency=explicit_insufficiency,
    )


def _outcome(
    reasons: tuple[ConvergenceReason, ...],
    current: ConvergenceObservation,
    *,
    evidence: ResearchConvergenceEvidence | None = None,
) -> ConvergenceOutcome:
    reason_set = set(reasons)
    if ConvergenceReason.cancelled in reason_set:
        return ConvergenceOutcome.cancelled
    if ConvergenceReason.explicit_insufficiency in reason_set:
        return ConvergenceOutcome.insufficient
    if ConvergenceReason.coverage_and_answerability in reason_set:
        return ConvergenceOutcome.converged
    if reason_set & {
        ConvergenceReason.iteration_limit,
        ConvergenceReason.tool_limit,
        ConvergenceReason.token_limit,
        ConvergenceReason.time_limit,
    }:
        return ConvergenceOutcome.budget_exhausted
    answerable = (
        evidence.answerable
        if evidence is not None
        else (
            current.required_claims > 0
            and current.verified_answerable_claims == current.required_claims
            and current.blocking_gap_count == 0
        )
    )
    return (
        ConvergenceOutcome.converged if answerable else ConvergenceOutcome.insufficient
    )


__all__ = [
    "ConvergenceDecision",
    "AnswerVerificationStatus",
    "ConvergenceError",
    "ConvergenceErrorCode",
    "ConvergenceObservation",
    "ConvergenceOutcome",
    "ConvergencePolicy",
    "ConvergenceReason",
    "ConvergenceService",
    "ResearchConvergenceEvidence",
    "create_convergence_observation",
    "create_research_convergence_evidence",
]
