# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Argument parser construction for the runtime CLI."""

from __future__ import annotations

import argparse

from bijux_canon_runtime.interfaces.cli.v2_parser import add_v2_commands
from bijux_canon_runtime.model.execution.command_modes import (
    DRY_RUN_COMMAND,
    PLAN_COMMAND,
    RUN_COMMAND,
    UNSAFE_RUN_COMMAND,
)


def build_parser(*, prog_name: str) -> argparse.ArgumentParser:
    """Build the runtime CLI parser."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=(
            "All completed runs are expected to be replayable unless explicitly "
            "documented otherwise."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{v2,init}")
    add_v2_commands(subparsers)

    init_parser = subparsers.add_parser(
        "init",
        help="Atomically initialize or validate a local Runtime workspace.",
    )
    init_parser.add_argument("--workspace", required=True)
    init_parser.add_argument(
        "--model",
        help=(
            "Optional materialized model directory containing model.lock.json; "
            "omit it for an offline lexical workspace. Relative paths resolve "
            "from the calling directory."
        ),
    )
    init_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser(
        RUN_COMMAND,
    )
    run_parser.add_argument("manifest")
    run_parser.add_argument("--policy", required=True)
    run_parser.add_argument("--db-path", required=True)
    run_parser.add_argument("--strict-determinism", action="store_true")
    run_parser.add_argument("--json", action="store_true")

    replay_parser = subparsers.add_parser(
        "replay",
    )
    replay_parser.add_argument("manifest")
    replay_parser.add_argument("--policy", required=True)
    replay_parser.add_argument("--run-id", required=True)
    replay_parser.add_argument("--tenant-id", required=True)
    replay_parser.add_argument("--db-path", required=True)
    replay_parser.add_argument("--strict-determinism", action="store_true")
    replay_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser(
        "inspect",
    )
    inspect_subparsers = inspect_parser.add_subparsers(dest="inspect_command")
    inspect_run_parser = inspect_subparsers.add_parser(
        RUN_COMMAND,
    )
    inspect_run_parser.add_argument("run_id")
    inspect_run_parser.add_argument("--tenant-id", required=True)
    inspect_run_parser.add_argument("--db-path", required=True)
    inspect_run_parser.add_argument("--json", action="store_true")

    plan_parser = subparsers.add_parser(
        PLAN_COMMAND,
    )
    plan_parser.add_argument("manifest")
    plan_parser.add_argument("--db-path")
    plan_parser.add_argument("--json", action="store_true")

    dry_run_parser = subparsers.add_parser(
        DRY_RUN_COMMAND,
    )
    dry_run_parser.add_argument("manifest")
    dry_run_parser.add_argument("--db-path", required=True)
    dry_run_parser.add_argument("--strict-determinism", action="store_true")
    dry_run_parser.add_argument("--json", action="store_true")

    unsafe_parser = subparsers.add_parser(
        UNSAFE_RUN_COMMAND,
    )
    unsafe_parser.add_argument("manifest")
    unsafe_parser.add_argument("--db-path", required=True)
    unsafe_parser.add_argument("--strict-determinism", action="store_true")
    unsafe_parser.add_argument("--json", action="store_true")

    diff_parser = subparsers.add_parser(
        "diff",
    )
    diff_subparsers = diff_parser.add_subparsers(dest="diff_command")
    diff_run_parser = diff_subparsers.add_parser(
        RUN_COMMAND,
    )
    diff_run_parser.add_argument("run_a")
    diff_run_parser.add_argument("run_b")
    diff_run_parser.add_argument("--tenant-id", required=True)
    diff_run_parser.add_argument("--db-path", required=True)
    diff_run_parser.add_argument("--json", action="store_true")

    explain_parser = subparsers.add_parser(
        "explain",
    )
    explain_subparsers = explain_parser.add_subparsers(dest="explain_command")
    explain_failure_parser = explain_subparsers.add_parser(
        "failure",
    )
    explain_failure_parser.add_argument("run_id")
    explain_failure_parser.add_argument("--tenant-id", required=True)
    explain_failure_parser.add_argument("--db-path", required=True)
    explain_failure_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate",
    )
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    validate_db_parser = validate_subparsers.add_parser(
        "db",
    )
    validate_db_parser.add_argument("--db-path", required=True)
    validate_db_parser.add_argument("--json", action="store_true")
    return parser


__all__ = ["build_parser"]
