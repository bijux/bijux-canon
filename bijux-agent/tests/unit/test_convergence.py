from __future__ import annotations

import pytest

from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceConfig,
    ConvergenceMonitor,
    ConvergenceReason,
    default_convergence_config,
)


def test_convergence_detects_stable_scores() -> None:
    monitor = ConvergenceMonitor(
        config=ConvergenceConfig(
            epsilon=1e-4,
            identical_verdicts=2,
            confidence_tolerance=0.01,
            window_size=3,
        )
    )
    monitor.record({"correctness": 0.9}, DecisionOutcome.PASS, 0.95)
    monitor.record({"correctness": 0.90005}, DecisionOutcome.PASS, 0.951)
    assert monitor.has_converged()


def test_convergence_detects_identical_verdicts() -> None:
    monitor = ConvergenceMonitor(
        config=ConvergenceConfig(
            epsilon=1e-3,
            identical_verdicts=3,
            confidence_tolerance=0.05,
            window_size=3,
        )
    )
    monitor.record({"risk": 0.1}, DecisionOutcome.PASS, 0.8)
    monitor.record({"risk": 0.15}, DecisionOutcome.PASS, 0.82)
    monitor.record({"risk": 0.05}, DecisionOutcome.PASS, 0.81)
    assert monitor.has_converged()


def test_last_confidence_reports_latest_value() -> None:
    monitor = ConvergenceMonitor(config=default_convergence_config())
    assert monitor.last_confidence() is None
    monitor.record({"score": 0.6}, DecisionOutcome.PASS, 0.66)
    assert monitor.last_confidence() == 0.66


def test_convergence_detects_oscillation() -> None:
    monitor = ConvergenceMonitor(config=default_convergence_config())
    monitor.record({"score": 0.6}, DecisionOutcome.PASS, 0.95)
    monitor.record({"score": 0.61}, DecisionOutcome.VETO, 0.96)
    monitor.record({"score": 0.62}, DecisionOutcome.PASS, 0.97)
    assert not monitor.has_converged()
    assert monitor.trace_metadata[-1]["converged"] is False


def test_convergence_confidence_only_is_insufficient() -> None:
    monitor = ConvergenceMonitor(config=default_convergence_config())
    monitor.record({"score": 0.5}, DecisionOutcome.PASS, 0.99)
    monitor.record({"score": 0.51}, DecisionOutcome.VETO, 0.99)
    assert not monitor.has_converged()
    last_snapshot = monitor.trace_metadata[-1]
    assert last_snapshot["convergence_type"] is None


def test_convergence_hash_is_deterministic() -> None:
    sequence = [
        ({"score": 0.5}, DecisionOutcome.PASS, 0.9),
        ({"score": 0.52}, DecisionOutcome.PASS, 0.92),
        ({"score": 0.53}, DecisionOutcome.PASS, 0.93),
    ]
    config = ConvergenceConfig(
        epsilon=1e-3,
        identical_verdicts=2,
        confidence_tolerance=0.01,
        window_size=3,
    )
    monitor_a = ConvergenceMonitor(config=config)
    monitor_b = ConvergenceMonitor(config=config)

    for scores, verdict, confidence in sequence:
        monitor_a.record(scores, verdict, confidence)
        monitor_b.record(scores, verdict, confidence)

    hash_a = monitor_a.trace_metadata[-1]["convergence_hash"]
    hash_b = monitor_b.trace_metadata[-1]["convergence_hash"]
    assert hash_a == hash_b
    assert monitor_a.debug_state()["convergence_hash"] == hash_a
    assert monitor_a.convergence_reason == ConvergenceReason.CONFIDENCE_ONLY


def test_convergence_replay_is_stable() -> None:
    config = ConvergenceConfig(
        epsilon=1e-3,
        identical_verdicts=2,
        confidence_tolerance=0.02,
        window_size=3,
    )
    sequence = [
        ({"score": 0.5}, DecisionOutcome.PASS, 0.92),
        ({"score": 0.51}, DecisionOutcome.PASS, 0.93),
        ({"score": 0.52}, DecisionOutcome.PASS, 0.94),
    ]
    monitor = ConvergenceMonitor(config=config)
    history: list[tuple[dict[str, float], DecisionOutcome, float]] = []
    for scores, verdict, confidence in sequence:
        monitor.record(scores, verdict, confidence)
        history.append((scores, verdict, confidence))
    replay = ConvergenceMonitor(config=config)
    for scores, verdict, confidence in history:
        replay.record(scores, verdict, confidence)
    assert (
        replay.trace_metadata[-1]["converged"]
        == monitor.trace_metadata[-1]["converged"]
    )
    assert replay.convergence_hash == monitor.convergence_hash
    assert replay.convergence_reason == monitor.convergence_reason


def test_convergence_metadata_ordering_enforced() -> None:
    monitor = ConvergenceMonitor(config=default_convergence_config())
    monitor.record({"score": 0.3}, DecisionOutcome.PASS, 0.6)
    monitor.record({"score": 0.31}, DecisionOutcome.PASS, 0.62)
    snapshot = list(monitor.trace_metadata)
    bad_order = list(snapshot[::-1])
    with pytest.raises(RuntimeError):
        ConvergenceMonitor.validate_trace_metadata(bad_order)


def test_missing_convergence_config_is_error() -> None:
    with pytest.raises(
        ValueError, match="ConvergenceConfig must be provided explicitly"
    ):
        ConvergenceMonitor()


def test_convergence_high_confidence_wrong_verdict() -> None:
    monitor = ConvergenceMonitor(
        config=ConvergenceConfig(
            epsilon=1e-4,
            identical_verdicts=2,
            confidence_tolerance=0.01,
            window_size=3,
        )
    )
    monitor.record({"score": 0.9}, DecisionOutcome.PASS, 0.99)
    monitor.record({"score": 0.91}, DecisionOutcome.VETO, 0.98)
    monitor.record({"score": 0.915}, DecisionOutcome.PASS, 0.995)
    assert not monitor.has_converged()
    assert monitor.trace_metadata[-1]["converged"] is False


def test_convergence_low_confidence_can_still_converge() -> None:
    monitor = ConvergenceMonitor(
        config=ConvergenceConfig(
            epsilon=1e-2,
            identical_verdicts=2,
            confidence_tolerance=0.05,
            window_size=3,
        )
    )
    monitor.record({"score": 0.4}, DecisionOutcome.PASS, 0.2)
    monitor.record({"score": 0.402}, DecisionOutcome.PASS, 0.22)
    assert monitor.has_converged()
    assert monitor.trace_metadata[-1]["converged"] is True
