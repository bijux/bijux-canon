from __future__ import annotations

from bijux_canon_agent.enums import DecisionOutcome
from bijux_canon_agent.pipeline.convergence.monitor import (
    ConvergenceReason,
    ConvergenceType,
)
from bijux_canon_agent.pipeline.convergence.snapshots import (
    build_convergence_snapshot,
    build_debug_state,
    compute_convergence_hash,
)


def test_compute_convergence_hash_is_stable() -> None:
    history = [
        ({"score": 0.5}, DecisionOutcome.PASS, 0.9),
        ({"score": 0.6}, DecisionOutcome.VETO, 0.8),
    ]

    assert compute_convergence_hash(history) == compute_convergence_hash(history)


def test_build_convergence_snapshot_serializes_enum_values() -> None:
    snapshot = build_convergence_snapshot(
        iteration=2,
        confidence=0.9,
        converged=True,
        convergence_type=ConvergenceType.MIXED,
        convergence_hash="abc",
        convergence_reason=ConvergenceReason.STABILITY,
    )

    assert snapshot["convergence_type"] == "mixed"
    assert snapshot["convergence_reason"] == "stability"


def test_build_debug_state_exposes_history_and_reason() -> None:
    debug_state = build_debug_state(
        history=[({"score": 0.5}, DecisionOutcome.PASS, 0.9)],
        trace_metadata=[{"iteration": 1}],
        convergence_type=ConvergenceType.VERDICT,
        convergence_hash="abc",
        convergence_reason=ConvergenceReason.CONFIDENCE_ONLY,
    )

    assert debug_state["convergence_hash"] == "abc"
    assert debug_state["convergence_reason"] == "confidence_only"
