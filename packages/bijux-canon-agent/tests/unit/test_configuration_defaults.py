"""Guard against implicit configuration paths."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_agent.application.workflow_graph.policy import (
    FailurePolicy,
    RetryPolicy,
)
from bijux_canon_agent.pipeline.convergence.monitor import (
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
    assert policy.fallback.preferred_models == [
        "gpt-4o-mini",
        "gpt-4o-mini-0",
        "gpt-3.5-turbo-1106",
    ]
    assert policy.scope_reduction.steps == [
        "collapse_documents",
        "summarize_sources",
        "reduce_to_key_points",
    ]
    assert policy.abort.critical_codes == ["FATAL", "SECURITY"]


def test_failure_policy_load_returns_default_retry(tmp_path: Path) -> None:
    missing_file = tmp_path / "does_not_exist.yaml"
    policy = FailurePolicy.load(missing_file)
    assert policy.retry == RetryPolicy()


def test_failure_policy_default_path_uses_repo_config() -> None:
    policy_path = FailurePolicy.default_path()
    expected = (
        Path(__file__).resolve().parents[4]
        / "packages"
        / "bijux-canon-agent"
        / "config"
        / "execution_policy.yaml"
    )
    assert policy_path == expected
    assert policy_path.is_file()


def test_failure_policy_load_default_matches_repo_config() -> None:
    policy_path = (
        Path(__file__).resolve().parents[4]
        / "packages"
        / "bijux-canon-agent"
        / "config"
        / "execution_policy.yaml"
    )
    assert FailurePolicy.load_default() == FailurePolicy.load(policy_path)
