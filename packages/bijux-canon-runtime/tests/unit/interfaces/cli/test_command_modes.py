# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.model.execution.command_modes import DRY_RUN_COMMAND
from bijux_canon_runtime.model.execution.command_modes import OBSERVE_COMMAND
from bijux_canon_runtime.model.execution.command_modes import PLAN_COMMAND
from bijux_canon_runtime.model.execution.command_modes import RUN_COMMAND
from bijux_canon_runtime.model.execution.command_modes import UNSAFE_RUN_COMMAND
from bijux_canon_runtime.model.execution.command_modes import run_mode_for_command
from bijux_canon_runtime.model.execution.run_mode import RunMode


@pytest.mark.parametrize(
    ("command", "mode"),
    [
        (PLAN_COMMAND, RunMode.PLAN),
        (DRY_RUN_COMMAND, RunMode.DRY_RUN),
        (RUN_COMMAND, RunMode.LIVE),
        (OBSERVE_COMMAND, RunMode.OBSERVE),
        (UNSAFE_RUN_COMMAND, RunMode.UNSAFE),
    ],
)
def test_run_mode_for_command_uses_canonical_mapping(
    command: str, mode: RunMode
) -> None:
    assert run_mode_for_command(command) is mode


def test_parser_accepts_canonical_runtime_command_names() -> None:
    parser = build_parser(prog_name="bijux-canon-runtime")
    command_args = {
        PLAN_COMMAND: [PLAN_COMMAND, "flow.json"],
        DRY_RUN_COMMAND: [DRY_RUN_COMMAND, "flow.json", "--db-path", "runs.duckdb"],
        RUN_COMMAND: [
            RUN_COMMAND,
            "flow.json",
            "--policy",
            "policy.json",
            "--db-path",
            "runs.duckdb",
        ],
        UNSAFE_RUN_COMMAND: [
            UNSAFE_RUN_COMMAND,
            "flow.json",
            "--db-path",
            "runs.duckdb",
        ],
    }

    for command, argv in command_args.items():
        args = parser.parse_args(argv)
        assert args.command == command
