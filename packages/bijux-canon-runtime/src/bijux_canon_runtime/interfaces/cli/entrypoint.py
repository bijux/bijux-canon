# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for cli/entrypoint.py."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from bijux_canon_runtime.interfaces.cli.execution_commands import (
    execute_manifest_command,
    execute_manifest_command_with_runner,
    replay_run,
)
from bijux_canon_runtime.application.execute_flow import execute_flow
from bijux_canon_runtime.interfaces.cli.manifest_loader import load_manifest
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.policy_loader import load_policy
from bijux_canon_runtime.interfaces.cli.store_commands import (
    diff_runs,
    explain_failure,
    inspect_run,
    validate_db,
)
_load_manifest = load_manifest
_load_policy = load_policy
_inspect_run = inspect_run
_diff_runs = diff_runs
_explain_failure = explain_failure
_validate_db = validate_db
_replay_run = replay_run


# Stable commands: plan, dry-run, run, unsafe-run, replay, inspect, diff, explain, validate.
# The CLI is not the primary API surface; contract-first integration should use the API schema.
EXIT_FAILURE = 1
EXIT_CONTRACT_VIOLATION = 2


def main() -> None:
    """Execute main and enforce its contract."""
    prog_name = (
        Path(sys.argv[0]).name if sys.argv and sys.argv[0] else "bijux-canon-runtime"
    )
    parser = build_parser(prog_name=prog_name)
    args = parser.parse_args()
    if args.command == "inspect" and args.inspect_command == "run":
        _inspect_run(args, json_output=args.json)
        return
    if args.command == "replay":
        _replay_run(args, json_output=args.json)
        return
    if (
        args.command == "diff" and args.diff_command == "run"
    ):
        _diff_runs(args, json_output=args.json)
        return
    if args.command == "explain" and args.explain_command == "failure":
        _explain_failure(args, json_output=args.json)
        return
    if args.command == "validate" and args.validate_command == "db":
        _validate_db(args, json_output=args.json)
        return
    execute_manifest_command_with_runner(args, execute_flow_fn=execute_flow)
