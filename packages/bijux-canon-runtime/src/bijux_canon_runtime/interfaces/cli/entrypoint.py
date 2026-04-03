# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for cli/entrypoint.py."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

from bijux_canon_runtime.core.errors import ConfigurationError, classify_failure
from bijux_canon_runtime.interfaces.cli.manifest_loader import load_manifest
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.policy_loader import load_policy
from bijux_canon_runtime.interfaces.cli.result_rendering import render_result
from bijux_canon_runtime.interfaces.cli.store_commands import (
    diff_runs,
    explain_failure,
    inspect_run,
    validate_db,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.application.replay_store import replay_with_store
from bijux_canon_runtime.ontology import (
    DeterminismLevel,
)
from bijux_canon_runtime.ontology.ids import (
    RunID,
    TenantID,
)
_load_manifest = load_manifest
_load_policy = load_policy
_inspect_run = inspect_run
_diff_runs = diff_runs
_explain_failure = explain_failure
_validate_db = validate_db


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

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)

    command = args.command
    config = ExecutionConfig.from_command(command)
    config = replace(config, determinism_level=manifest.determinism_level)
    if getattr(args, "db_path", None):
        config = ExecutionConfig(
            mode=config.mode,
            determinism_level=manifest.determinism_level,
            execution_store=DuckDBExecutionWriteStore(Path(args.db_path)),
        )
    if getattr(args, "strict_determinism", False):
        config = replace(config, strict_determinism=True)
    if getattr(args, "policy", None):
        policy = _load_policy(Path(args.policy))
        config = replace(config, verification_policy=policy)
    try:
        result = execute_flow(manifest, config=config)
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            print(str(exc), file=sys.stderr)
            raise SystemExit(EXIT_CONTRACT_VIOLATION) from exc
        try:
            failure_class = classify_failure(exc)
        except KeyError:
            raise
        print(f"Failure: {failure_class.value}", file=sys.stderr)
        raise SystemExit(EXIT_FAILURE) from exc
    render_result(command, result, json_output=args.json)


def _replay_run(args: argparse.Namespace, *, json_output: bool) -> None:
    """Internal helper; not part of the public API."""
    manifest = _load_manifest(Path(args.manifest))
    policy = _load_policy(Path(args.policy))
    planner = ExecutionPlanner()
    resolved_flow = planner.resolve(manifest)
    read_store = DuckDBExecutionReadStore(Path(args.db_path))
    write_store = DuckDBExecutionWriteStore(Path(args.db_path))
    config = ExecutionConfig(
        mode=_config_mode_for_replay(),
        determinism_level=manifest.determinism_level,
        execution_store=write_store,
        execution_read_store=read_store,
        verification_policy=policy,
        strict_determinism=bool(args.strict_determinism),
    )
    diff, result = replay_with_store(
        store=read_store,
        run_id=RunID(args.run_id),
        tenant_id=TenantID(args.tenant_id),
        resolved_flow=resolved_flow,
        config=config,
    )
    if json_output:
        payload = {
            "diff": _normalize_for_json(diff, normalize_timestamps=True),
            "trace": _normalize_for_json(
                asdict(result.trace), normalize_timestamps=True
            ),
            "run_id": str(result.run_id),
        }
        print(json.dumps(payload, sort_keys=True))
        if diff:
            reason_code = next(iter(diff))
            print(reason_code, file=sys.stderr)
            raise SystemExit(EXIT_CONTRACT_VIOLATION)
        return
    if diff:
        reason_code = next(iter(diff))
        print(reason_code)
        raise SystemExit(EXIT_CONTRACT_VIOLATION)
    else:
        print(f"Replay clean: run_id={result.run_id}")


def _config_mode_for_replay() -> RunMode:
    """Internal helper; not part of the public API."""
    return RunMode.LIVE
