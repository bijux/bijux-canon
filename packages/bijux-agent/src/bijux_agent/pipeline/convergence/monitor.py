"""Helpers tracking when the pipeline has settled on stable judgments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from statistics import mean
from typing import Any, Protocol, cast
import warnings

from bijux_agent.enums import DecisionOutcome

DEFAULT_EPSILON = 1e-3
DEFAULT_IDENTICAL_VERDICTS = 2
DEFAULT_CONFIDENCE_TOLERANCE = 0.01
DEFAULT_WINDOW_SIZE = 3


def _aggregate_scores(scores: Mapping[str, float]) -> float:
    if not scores:
        return 0.0
    return mean(scores.values())


@dataclass(frozen=True)
class ConvergenceConfig:
    epsilon: float
    identical_verdicts: int
    confidence_tolerance: float
    window_size: int


@dataclass
class DecisionStabilityWindow:
    """Compatibility adapter for the original convergence snapshot config."""

    min_iterations: int = DEFAULT_IDENTICAL_VERDICTS
    window_size: int = DEFAULT_WINDOW_SIZE

    def __post_init__(self) -> None:
        warnings.warn(
            "DecisionStabilityWindow is retired; provide ConvergenceConfig directly",
            DeprecationWarning,
            stacklevel=2,
        )


def _config_from_window(window: DecisionStabilityWindow) -> ConvergenceConfig:
    return ConvergenceConfig(
        epsilon=DEFAULT_EPSILON,
        identical_verdicts=window.min_iterations,
        confidence_tolerance=DEFAULT_CONFIDENCE_TOLERANCE,
        window_size=window.window_size,
    )


class ConvergenceType(str, Enum):
    SCORE = "score"
    VERDICT = "verdict"
    CONFIDENCE = "confidence"
    MIXED = "mixed"


class ConvergenceReason(str, Enum):
    STABILITY = "stability"
    OSCILLATION = "oscillation"
    MAX_ITERATIONS = "max_iterations"
    CONFIDENCE_ONLY = "confidence_only"


@dataclass(frozen=True)
class ConvergenceDecision:
    converged: bool
    convergence_type: ConvergenceType
    convergence_reason: ConvergenceReason
    strategy: str


class ConvergenceStrategy(Protocol):
    @property
    def name(self) -> str: ...

    def evaluate(
        self,
        history: list[tuple[Mapping[str, float], DecisionOutcome, float]],
        config: ConvergenceConfig,
    ) -> ConvergenceDecision | None:
        """Return a decision when convergence is reached."""


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


class ConvergenceMonitor:
    """Track convergence metadata and annotate the trace.

    Records confidence/verdict history, convergence hashes, and the trigger type
    so downstream replay can verify deterministic behavior.
    """

    def __init__(
        self,
        *,
        config: ConvergenceConfig | None = None,
        window_config: DecisionStabilityWindow | None = None,
        strategy: ConvergenceStrategy | None = None,
    ) -> None:
        if config is None and window_config is None:
            raise ValueError("ConvergenceConfig must be provided explicitly")
        if config is None and window_config is not None:
            config = _config_from_window(window_config)
        self.config: ConvergenceConfig = cast(ConvergenceConfig, config)
        self.strategy = strategy or default_convergence_strategy()
        self.history: list[tuple[Mapping[str, float], DecisionOutcome, float]] = []
        self.trace_metadata: list[dict[str, Any]] = []
        self.convergence_type: ConvergenceType | None = None
        self.convergence_hash: str | None = None
        self.convergence_reason: ConvergenceReason | None = None

    def record(
        self,
        scores: Mapping[str, float],
        verdict: DecisionOutcome,
        confidence: float,
    ) -> None:
        self.history.append((dict(scores), verdict, confidence))
        self._update_convergence_hash()
        converged = self.has_converged()
        snapshot = {
            "iteration": len(self.history),
            "last_confidence": confidence,
            "converged": converged,
            "convergence_type": self.convergence_type.value
            if self.convergence_type
            else None,
            "convergence_hash": self.convergence_hash,
            "convergence_reason": self.convergence_reason.value
            if self.convergence_reason
            else None,
        }
        self.trace_metadata.append(snapshot)

    def has_converged(self) -> bool:
        decision = self.strategy.evaluate(self.history, self.config)
        if decision is None:
            self.convergence_type = None
            self.convergence_reason = None
            return False
        self.convergence_type = decision.convergence_type
        self.convergence_reason = decision.convergence_reason
        return decision.converged

    def last_confidence(self) -> float | None:
        return self.history[-1][2] if self.history else None

    def _update_convergence_hash(self) -> str:
        window = self.history[-self.config.window_size :]
        if not window:
            self.convergence_hash = ""
            return self.convergence_hash
        normalized: list[tuple[tuple[tuple[str, float], ...], str]] = []
        for scores, verdict, _ in window:
            normalized.append(
                (
                    tuple(sorted(scores.items())),
                    verdict.value,
                )
            )
        payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
        hashed = hashlib.sha256(payload.encode()).hexdigest()
        self.convergence_hash = hashed
        return hashed

    def debug_state(self) -> dict[str, Any]:
        return {
            "history": list(self.history),
            "trace_metadata": list(self.trace_metadata),
            "convergence_type": self.convergence_type.value
            if self.convergence_type
            else None,
            "convergence_hash": self.convergence_hash,
            "convergence_reason": self.convergence_reason.value
            if self.convergence_reason
            else None,
        }

    def set_convergence_reason(self, reason: ConvergenceReason) -> None:
        """Override the inferred convergence reason."""
        self.convergence_reason = reason

    @staticmethod
    def validate_trace_metadata(snapshot: list[dict[str, Any]]) -> None:
        iterations = [entry.get("iteration") for entry in snapshot]
        for i in range(len(iterations) - 1):
            current = iterations[i]
            nxt = iterations[i + 1]
            if current is not None and nxt is not None and current >= nxt:
                raise RuntimeError("Convergence metadata must be ordered by iteration")


def default_convergence_config() -> ConvergenceConfig:
    return ConvergenceConfig(
        epsilon=DEFAULT_EPSILON,
        identical_verdicts=DEFAULT_IDENTICAL_VERDICTS,
        confidence_tolerance=DEFAULT_CONFIDENCE_TOLERANCE,
        window_size=DEFAULT_WINDOW_SIZE,
    )
