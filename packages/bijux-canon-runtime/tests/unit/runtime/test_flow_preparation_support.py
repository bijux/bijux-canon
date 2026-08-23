from __future__ import annotations

import pytest

from bijux_canon_runtime.application.flow_execution_models import ExecutionConfig
from bijux_canon_runtime.application.flow_preparation_support import (
    effective_execution_config,
)
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.runtime.context import RunMode


def test_effective_execution_config_enables_resolved_strict_mode() -> None:
    settings = resolve_runtime_configuration(
        environment={"BIJUX_CANON_RUNTIME_STRICT": "1"}
    )
    config = ExecutionConfig(
        mode=RunMode.LIVE,
        determinism_level=None,
        strict_determinism=False,
        runtime_configuration=settings,
    )

    updated = effective_execution_config(config)

    assert updated.strict_determinism is True


def test_effective_execution_config_resolves_one_default_authority(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(tmp_path / "workspace"))

    updated = effective_execution_config(
        ExecutionConfig(mode=RunMode.LIVE, determinism_level=None)
    )

    assert updated.runtime_configuration is not None
    assert (
        updated.runtime_configuration.require_workspace_layout().root
        == (tmp_path / "workspace").resolve()
    )


def test_strict_configuration_rejects_best_effort_modes() -> None:
    settings = resolve_runtime_configuration(environment={"AGENTIC_FLOWS_STRICT": "1"})
    config = ExecutionConfig(
        mode=RunMode.DRY_RUN,
        determinism_level=None,
        runtime_configuration=settings,
    )

    with pytest.raises(
        ValueError, match="BIJUX_CANON_RUNTIME_STRICT forbids best-effort execution"
    ):
        effective_execution_config(config)
