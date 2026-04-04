"""Convergence strategy implementations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from statistics import mean
from typing import cast

from bijux_canon_agent.enums import DecisionOutcome

from .models import (
    ConvergenceConfig,
    ConvergenceDecision,
    ConvergenceReason,
    ConvergenceStrategy,
    ConvergenceType,
)


def _aggregate_scores(scores: Mapping[str, float]) -> float:
    if not scores:
        return 0.0
    return mean(scores.values())


@dataclass(frozen=True)
class MixedStabilityStrategy:
    """Converges when scores, confidence, and verdict are stable."""

    name: str = "mixed_stability"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        if len(history) < 2:
            return None
        last_scores, last_verdict, last_confidence = history[-1]
        prev_scores, prev_verdict, prev_confidence = history[-2]
        score_delta = abs(
            _aggregate_scores(last_scores) - _aggregate_scores(prev_scores)
        )
        confidence_delta = abs(last_confidence - prev_confidence)
        if (
            score_delta <= config.epsilon
            and confidence_delta <= config.confidence_tolerance
            and last_verdict == prev_verdict
        ):
            return ConvergenceDecision(
                converged=True,
                convergence_type=ConvergenceType.MIXED,
                convergence_reason=ConvergenceReason.STABILITY,
                strategy=self.name,
            )
        return None


@dataclass(frozen=True)
class VerdictStabilityStrategy:
    """Converges when the verdict repeats for a configured window."""

    name: str = "verdict_stability"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        if len(history) < config.identical_verdicts:
            return None
        recent = history[-config.identical_verdicts :]
        verdicts = {entry[1] for entry in recent}
        if len(verdicts) == 1:
            return ConvergenceDecision(
                converged=True,
                convergence_type=ConvergenceType.VERDICT,
                convergence_reason=ConvergenceReason.CONFIDENCE_ONLY,
                strategy=self.name,
            )
        return None


@dataclass(frozen=True)
class OscillationStrategy:
    """Detect oscillations in verdicts within the window."""

    name: str = "oscillation"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        if len(history) < config.window_size:
            return None
        window = history[-config.window_size :]
        verdicts = [entry[1] for entry in window]
        if len(set(verdicts)) < 2:
            return None
        if len(verdicts) >= 3 and verdicts[-1] == verdicts[-3]:
            return ConvergenceDecision(
                converged=True,
                convergence_type=ConvergenceType.SCORE,
                convergence_reason=ConvergenceReason.OSCILLATION,
                strategy=self.name,
            )
        return None


@dataclass(frozen=True)
class AnyConvergenceStrategy:
    """Return the first convergence decision from any strategy."""

    strategies: tuple[ConvergenceStrategy, ...]
    name: str = "any"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        for strategy in self.strategies:
            decision = strategy.evaluate(history, config)
            if decision:
                return decision
        return None


@dataclass(frozen=True)
class AllConvergenceStrategy:
    """Require all strategies to converge."""

    strategies: tuple[ConvergenceStrategy, ...]
    name: str = "all"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        decisions = [strategy.evaluate(history, config) for strategy in self.strategies]
        if any(decision is None for decision in decisions):
            return None
        first = decisions[0]
        if first is None:
            return None
        return ConvergenceDecision(
            converged=True,
            convergence_type=first.convergence_type,
            convergence_reason=first.convergence_reason,
            strategy=self.name,
        )


@dataclass(frozen=True)
class QuorumConvergenceStrategy:
    """Require a minimum number of strategies to converge."""

    strategies: tuple[ConvergenceStrategy, ...]
    quorum: int
    name: str = "quorum"

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        decisions = [
            decision
            for decision in (
                strategy.evaluate(history, config) for strategy in self.strategies
            )
            if decision is not None
        ]
        if len(decisions) < self.quorum:
            return None
        first = decisions[0]
        return ConvergenceDecision(
            converged=True,
            convergence_type=first.convergence_type,
            convergence_reason=first.convergence_reason,
            strategy=self.name,
        )


def default_convergence_strategy() -> ConvergenceStrategy:
    return AnyConvergenceStrategy(
        strategies=cast(
            tuple[ConvergenceStrategy, ...],
            (
                MixedStabilityStrategy(),
                VerdictStabilityStrategy(),
            ),
        )
    )
