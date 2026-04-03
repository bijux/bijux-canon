# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Argument parser construction for the runtime CLI."""

from __future__ import annotations

import argparse


def build_parser(*, prog_name: str) -> argparse.ArgumentParser:
    """Build the runtime CLI parser."""
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=(
            "All completed runs are expected to be replayable unless explicitly "
            "documented otherwise."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help=(
            "Deterministic when strict mode and declared contracts are satisfied; "
            "output stability is guaranteed only within v1."
        ),
    )
    run_parser.add_argument("manifest")
    run_parser.add_argument("--policy", required=True)
    run_parser.add_argument("--db-path", required=True)
    run_parser.add_argument("--strict-determinism", action="store_true")
    run_parser.add_argument("--json", action="store_true")

    replay_parser = subparsers.add_parser(
        "replay",
        help=(
            "Replays enforce declared determinism thresholds; "
            "output stability is guaranteed only within v1."
        ),
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
        help=(
            "Inspection reflects persisted state deterministically; "
            "output stability is guaranteed only within v1."
        ),
    )
    inspect_subparsers = inspect_parser.add_subparsers(dest="inspect_command")
    inspect_run_parser = inspect_subparsers.add_parser(
        "run",
        help=argparse.SUPPRESS,
    )
    inspect_run_parser.add_argument("run_id")
    inspect_run_parser.add_argument("--tenant-id", required=True)
    inspect_run_parser.add_argument("--db-path", required=True)
    inspect_run_parser.add_argument("--json", action="store_true")

    plan_parser = subparsers.add_parser(
        "plan",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    plan_parser.add_argument("manifest")
    plan_parser.add_argument("--db-path")
    plan_parser.add_argument("--json", action="store_true")

    dry_run_parser = subparsers.add_parser(
        "dry-run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    dry_run_parser.add_argument("manifest")
    dry_run_parser.add_argument("--db-path", required=True)
    dry_run_parser.add_argument("--strict-determinism", action="store_true")
    dry_run_parser.add_argument("--json", action="store_true")

    unsafe_parser = subparsers.add_parser(
        "unsafe-run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    unsafe_parser.add_argument("manifest")
    unsafe_parser.add_argument("--db-path", required=True)
    unsafe_parser.add_argument("--strict-determinism", action="store_true")
    unsafe_parser.add_argument("--json", action="store_true")

    diff_parser = subparsers.add_parser(
        "diff",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    diff_subparsers = diff_parser.add_subparsers(dest="diff_command")
    diff_run_parser = diff_subparsers.add_parser(
        "run",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    diff_run_parser.add_argument("run_a")
    diff_run_parser.add_argument("run_b")
    diff_run_parser.add_argument("--tenant-id", required=True)
    diff_run_parser.add_argument("--db-path", required=True)
    diff_run_parser.add_argument("--json", action="store_true")

    explain_parser = subparsers.add_parser(
        "explain",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    explain_subparsers = explain_parser.add_subparsers(dest="explain_command")
    explain_failure_parser = explain_subparsers.add_parser(
        "failure",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    explain_failure_parser.add_argument("run_id")
    explain_failure_parser.add_argument("--tenant-id", required=True)
    explain_failure_parser.add_argument("--db-path", required=True)
    explain_failure_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser(
        "validate",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    validate_db_parser = validate_subparsers.add_parser(
        "db",
        help=argparse.SUPPRESS,
        description=argparse.SUPPRESS,
    )
    validate_db_parser.add_argument("--db-path", required=True)
    validate_db_parser.add_argument("--json", action="store_true")
    return parser


__all__ = ["build_parser"]
