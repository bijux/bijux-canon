from __future__ import annotations

from bijux_canon_runtime.application.flow_execution_models import ExecutionConfig
from bijux_canon_runtime.application.flow_preparation_support import (
    effective_execution_config,
)
from bijux_canon_runtime.runtime.context import RunMode
import pytest


def test_effective_execution_config_enables_strict_mode_from_runtime_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_STRICT", "1")
    config = ExecutionConfig(
        mode=RunMode.LIVE,
        determinism_level=None,
        strict_determinism=False,
    )

    updated = effective_execution_config(config)

    assert updated.strict_determinism is True


def test_effective_execution_config_rejects_best_effort_modes_under_strict_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTIC_FLOWS_STRICT", "1")
    config = ExecutionConfig(
        mode=RunMode.DRY_RUN,
        determinism_level=None,
    )

    with pytest.raises(
        ValueError, match="BIJUX_CANON_RUNTIME_STRICT forbids best-effort execution"
    ):
        effective_execution_config(config)
