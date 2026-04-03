from __future__ import annotations

from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.convergence.monitor import (
    AllConvergenceStrategy,
    AnyConvergenceStrategy,
    ConvergenceConfig,
    MixedStabilityStrategy,
    OscillationStrategy,
    QuorumConvergenceStrategy,
    VerdictStabilityStrategy,
)


def test_any_strategy_returns_first_match() -> None:
    config = ConvergenceConfig(
        epsilon=1e-4,
        identical_verdicts=2,
        confidence_tolerance=0.01,
        window_size=3,
    )
    history = [
        ({"score": 0.1}, DecisionOutcome.PASS, 0.9),
        ({"score": 0.2}, DecisionOutcome.PASS, 0.91),
    ]
    strategy = AnyConvergenceStrategy(
        strategies=(MixedStabilityStrategy(), VerdictStabilityStrategy())
    )
    decision = strategy.evaluate(history, config)
    assert decision is not None
    assert decision.convergence_reason.value == "confidence_only"


def test_all_strategy_requires_all() -> None:
    config = ConvergenceConfig(
        epsilon=1e-4,
        identical_verdicts=2,
        confidence_tolerance=0.01,
        window_size=3,
    )
    history = [
        ({"score": 0.1}, DecisionOutcome.PASS, 0.9),
        ({"score": 0.2}, DecisionOutcome.PASS, 0.91),
    ]
    strategy = AllConvergenceStrategy(
        strategies=(MixedStabilityStrategy(), VerdictStabilityStrategy())
    )
    assert strategy.evaluate(history, config) is None


def test_quorum_strategy_accepts_threshold() -> None:
    config = ConvergenceConfig(
        epsilon=1e-2,
        identical_verdicts=2,
        confidence_tolerance=0.05,
        window_size=3,
    )
    history = [
        ({"score": 0.4}, DecisionOutcome.PASS, 0.6),
        ({"score": 0.401}, DecisionOutcome.PASS, 0.61),
        ({"score": 0.402}, DecisionOutcome.PASS, 0.62),
    ]
    strategy = QuorumConvergenceStrategy(
        strategies=(
            MixedStabilityStrategy(),
            VerdictStabilityStrategy(),
            OscillationStrategy(),
        ),
        quorum=2,
    )
    decision = strategy.evaluate(history, config)
    assert decision is not None
    assert decision.converged is True
