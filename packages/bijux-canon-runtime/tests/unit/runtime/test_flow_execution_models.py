from __future__ import annotations

import pytest

from bijux_canon_runtime.application.flow_execution_models import ExecutionConfig
from bijux_canon_runtime.runtime.context import RunMode


@pytest.mark.parametrize(
    ("command", "mode"),
    [
        ("plan", RunMode.PLAN),
        ("dry-run", RunMode.DRY_RUN),
        ("run", RunMode.LIVE),
        ("observe", RunMode.OBSERVE),
        ("unsafe-run", RunMode.UNSAFE),
    ],
)
def test_execution_config_from_command_maps_command_to_run_mode(
    command: str, mode: RunMode
) -> None:
    config = ExecutionConfig.from_command(command)

    assert config.mode is mode
    assert config.determinism_level is None


def test_execution_config_from_command_rejects_unknown_command() -> None:
    with pytest.raises(ValueError, match="Unsupported command: unknown"):
        ExecutionConfig.from_command("unknown")
