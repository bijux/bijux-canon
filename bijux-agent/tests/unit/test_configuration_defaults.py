"""Guard against implicit configuration paths."""

from __future__ import annotations

from pathlib import Path

from bijux_agent.orchestrator.policy import FailurePolicy, RetryPolicy
from bijux_agent.pipeline.convergence.monitor import (
    ConvergenceMonitor,
    default_convergence_config,
)


def test_convergence_monitor_requires_explicit_config() -> None:
    config = default_convergence_config()
    monitor = ConvergenceMonitor(config=config)
    assert monitor.config == config


def test_failure_policy_uses_retry_defaults() -> None:
    policy = FailurePolicy()
    assert isinstance(policy.retry, RetryPolicy)
    assert policy.retry == RetryPolicy()


def test_failure_policy_load_returns_default_retry(tmp_path: Path) -> None:
    missing_file = tmp_path / "does_not_exist.yaml"
    policy = FailurePolicy.load(missing_file)
    assert policy.retry == RetryPolicy()
