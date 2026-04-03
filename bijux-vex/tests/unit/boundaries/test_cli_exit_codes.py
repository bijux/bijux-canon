# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest
from typer.testing import CliRunner

from bijux_vex.boundaries.cli import app as cli_app
from bijux_vex.core.contracts.execution_contract import ExecutionContract


def test_cli_exit_code_for_misuse():
    runner = CliRunner()
    # Missing required option should exit with typer code 2
    result = runner.invoke(cli_app.app, ["execute"], prog_name="bijux")
    assert result.exit_code == 2


def test_cli_exit_code_for_invariant():
    runner = CliRunner()
    result = runner.invoke(
        cli_app.app,
        [
            "execute",
            "--execution-contract",
            "deterministic",
            "--execution-intent",
            "exact_validation",
            "--vector",
            "[0,1]",
            "--artifact-id",
            "missing",
        ],
        prog_name="bijux",
    )
    assert result.exit_code in (3, 4)  # invariant or not found


def test_cli_exit_code_for_backend_unavailable():
    runner = CliRunner()
    result = runner.invoke(
        cli_app.app,
        [
            "execute",
            "--execution-contract",
            ExecutionContract.NON_DETERMINISTIC.value,
            "--execution-intent",
            "exploratory_search",
            "--execution-mode",
            "bounded",
            "--vector",
            "[0,1]",
            "--artifact-id",
            "art-1",
        ],
        prog_name="bijux",
    )
    assert result.exit_code != 0


def test_cli_capabilities_command_runs():
    runner = CliRunner()
    result = runner.invoke(cli_app.app, ["capabilities"], prog_name="bijux")
    assert result.exit_code == 0
    assert "supports_ann" in result.stdout
