from __future__ import annotations

from bijux_canon_agent.pipeline.convergence.models import (
    ConvergenceConfig,
    ConvergenceDecision,
    ConvergenceReason,
    ConvergenceType,
)


def test_convergence_config_keeps_runtime_thresholds() -> None:
    config = ConvergenceConfig(0.01, 2, 0.02, 3)

    assert config.identical_verdicts == 2
    assert config.window_size == 3


def test_convergence_decision_preserves_reason_and_type() -> None:
    decision = ConvergenceDecision(
        converged=True,
        convergence_type=ConvergenceType.MIXED,
        convergence_reason=ConvergenceReason.STABILITY,
        strategy="mixed_stability",
    )

    assert decision.converged is True
    assert decision.strategy == "mixed_stability"
