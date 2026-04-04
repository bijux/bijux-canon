"""Shared convergence models and contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from bijux_canon_agent.enums import DecisionOutcome


@dataclass(frozen=True)
class ConvergenceConfig:
    epsilon: float
    identical_verdicts: int
    confidence_tolerance: float
    window_size: int


class ConvergenceType(StrEnum):
    SCORE = "score"
    VERDICT = "verdict"
    CONFIDENCE = "confidence"
    MIXED = "mixed"


class ConvergenceReason(StrEnum):
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
