# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical runtime command names and their execution modes."""

from __future__ import annotations

from bijux_canon_runtime.model.execution.run_mode import RunMode

PLAN_COMMAND = "plan"
DRY_RUN_COMMAND = "dry-run"
RUN_COMMAND = "run"
OBSERVE_COMMAND = "observe"
UNSAFE_RUN_COMMAND = "unsafe-run"

RUN_MODE_BY_COMMAND = {
    PLAN_COMMAND: RunMode.PLAN,
    DRY_RUN_COMMAND: RunMode.DRY_RUN,
    RUN_COMMAND: RunMode.LIVE,
    OBSERVE_COMMAND: RunMode.OBSERVE,
    UNSAFE_RUN_COMMAND: RunMode.UNSAFE,
}
EXECUTION_TRACE_COMMANDS = frozenset({RUN_COMMAND, UNSAFE_RUN_COMMAND})


def run_mode_for_command(command: str) -> RunMode:
    """Return the execution mode for a canonical runtime command."""
    try:
        return RUN_MODE_BY_COMMAND[command]
    except KeyError as error:
        raise ValueError(f"Unsupported command: {command}") from error


__all__ = [
    "DRY_RUN_COMMAND",
    "EXECUTION_TRACE_COMMANDS",
    "OBSERVE_COMMAND",
    "PLAN_COMMAND",
    "RUN_COMMAND",
    "RUN_MODE_BY_COMMAND",
    "UNSAFE_RUN_COMMAND",
    "run_mode_for_command",
]
