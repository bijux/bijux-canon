# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Compute deterministic terminal decisions for bounded research cycles."""

from __future__ import annotations

from enum import StrEnum
import math
from typing import Literal, Self

from pydantic import field_validator, model_validator

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


class ConvergenceDecision(StableModel):
    """Content-addressed decision that can never continue past a stop condition."""

    schema_version: Literal["bijux.canon.reason.convergence_decision.v1"] = (
        "bijux.canon.reason.convergence_decision.v1"
    )
    artifact_id: str
    policy: ConvergencePolicy
    observation_artifact_ids: tuple[str, ...]
    current_graph_artifact_id: str
    outcome: ConvergenceOutcome
    stop: bool
    reasons: tuple[ConvergenceReason, ...]

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
        if tuple(sorted(set(self.reasons))) != self.reasons:
            raise ValueError("convergence reasons must be unique and sorted")
        continuing = self.outcome is ConvergenceOutcome.continue_research
        if continuing != (not self.stop):
            raise ValueError("only continue_research decisions may keep cycling")
        if continuing != (self.reasons == (ConvergenceReason.continue_research,)):
            raise ValueError("continuing requires the sole continue reason")
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
        self, observations: tuple[ConvergenceObservation, ...]
    ) -> ConvergenceDecision:
        """Return a terminal decision whenever any declared stop condition holds."""

        if not observations:
            raise ConvergenceError(
                ConvergenceErrorCode.empty_history,
                "convergence requires at least one observation",
            )
        self._validate_history(observations)
        current = observations[-1]
        reasons = self._terminal_reasons(observations)
        if not reasons:
            reasons = (ConvergenceReason.continue_research,)
            outcome = ConvergenceOutcome.continue_research
            stop = False
        else:
            outcome = _outcome(reasons, current)
            stop = True
        payload = {
            "schema_version": "bijux.canon.reason.convergence_decision.v1",
            "policy": self.policy.model_dump(mode="json"),
            "observation_artifact_ids": tuple(
                item.artifact_id for item in observations
            ),
            "current_graph_artifact_id": current.graph_artifact_id,
            "outcome": outcome.value,
            "stop": stop,
            "reasons": tuple(item.value for item in reasons),
        }
        return ConvergenceDecision(
            artifact_id=content_artifact_id(payload),
            policy=self.policy,
            observation_artifact_ids=tuple(item.artifact_id for item in observations),
            current_graph_artifact_id=current.graph_artifact_id,
            outcome=outcome,
            stop=stop,
            reasons=reasons,
        )

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
        self, observations: tuple[ConvergenceObservation, ...]
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
            current.required_claims > 0
            and current.verified_answerable_claims == current.required_claims
            and current.blocking_gap_count == 0
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
        return tuple(sorted(reasons))


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
        "coverage": coverage,
        "verified_answerable_claims": verified_answerable_claims,
        "required_claims": required_claims,
        "blocking_gap_count": blocking_gap_count,
        "new_evidence_count": new_evidence_count,
        "marginal_evidence_value": marginal_evidence_value,
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
    reasons: tuple[ConvergenceReason, ...], current: ConvergenceObservation
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
        current.required_claims > 0
        and current.verified_answerable_claims == current.required_claims
        and current.blocking_gap_count == 0
    )
    return (
        ConvergenceOutcome.converged if answerable else ConvergenceOutcome.insufficient
    )


__all__ = [
    "ConvergenceDecision",
    "ConvergenceError",
    "ConvergenceErrorCode",
    "ConvergenceObservation",
    "ConvergenceOutcome",
    "ConvergencePolicy",
    "ConvergenceReason",
    "ConvergenceService",
    "create_convergence_observation",
]
