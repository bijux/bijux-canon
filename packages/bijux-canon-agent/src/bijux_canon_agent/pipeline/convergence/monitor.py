"""Helpers tracking when the pipeline has settled on stable judgments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
import warnings

from bijux_canon_agent.enums import DecisionOutcome
from bijux_canon_agent.pipeline.convergence.models import (
    ConvergenceConfig,
    ConvergenceReason,
    ConvergenceStrategy,
    ConvergenceType,
)
from bijux_canon_agent.pipeline.convergence.snapshots import (
    build_convergence_snapshot,
    build_debug_state,
    compute_convergence_hash,
)
from bijux_canon_agent.pipeline.convergence.strategies import (
    AllConvergenceStrategy,
    AnyConvergenceStrategy,
    MixedStabilityStrategy,
    OscillationStrategy,
    QuorumConvergenceStrategy,
    VerdictStabilityStrategy,
    default_convergence_strategy,
)

DEFAULT_EPSILON = 1e-3
DEFAULT_IDENTICAL_VERDICTS = 2
DEFAULT_CONFIDENCE_TOLERANCE = 0.01
DEFAULT_WINDOW_SIZE = 3


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
        snapshot = build_convergence_snapshot(
            iteration=len(self.history),
            confidence=confidence,
            converged=converged,
            convergence_type=self.convergence_type,
            convergence_hash=self.convergence_hash,
            convergence_reason=self.convergence_reason,
        )
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
        self.convergence_hash = compute_convergence_hash(window)
        return self.convergence_hash

    def debug_state(self) -> dict[str, Any]:
        return build_debug_state(
            history=self.history,
            trace_metadata=self.trace_metadata,
            convergence_type=self.convergence_type,
            convergence_hash=self.convergence_hash,
            convergence_reason=self.convergence_reason,
        )

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


__all__ = [
    "AllConvergenceStrategy",
    "AnyConvergenceStrategy",
    "ConvergenceConfig",
    "ConvergenceMonitor",
    "ConvergenceReason",
    "ConvergenceStrategy",
    "ConvergenceType",
    "DecisionStabilityWindow",
    "MixedStabilityStrategy",
    "OscillationStrategy",
    "QuorumConvergenceStrategy",
    "VerdictStabilityStrategy",
    "default_convergence_config",
]
