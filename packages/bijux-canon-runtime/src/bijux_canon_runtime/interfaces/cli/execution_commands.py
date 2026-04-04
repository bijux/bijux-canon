# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Mutable execution commands for the runtime CLI."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    FlowRunResult,
    execute_flow,
)
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.application.replay_store import replay_with_store
from bijux_canon_runtime.core.errors import ConfigurationError, classify_failure
from bijux_canon_runtime.interfaces.cli.manifest_loader import load_manifest
from bijux_canon_runtime.interfaces.cli.policy_loader import load_policy
from bijux_canon_runtime.interfaces.cli.result_rendering import render_result
from bijux_canon_runtime.interfaces.cli.store_commands import normalize_for_json
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import RunID, TenantID

EXIT_FAILURE = 1
EXIT_CONTRACT_VIOLATION = 2


def execute_manifest_command(args: argparse.Namespace) -> None:
    """Execute a manifest-backed runtime CLI command."""
    execute_flow_fn = execute_flow
    execute_manifest_command_with_runner(args, execute_flow_fn=execute_flow_fn)


def execute_manifest_command_with_runner(
    args: argparse.Namespace,
    *,
    execute_flow_fn: Callable[..., FlowRunResult],
) -> None:
    """Execute a manifest-backed runtime CLI command with an injected runner."""
    manifest = load_manifest(Path(args.manifest))
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
        policy = load_policy(Path(args.policy))
        config = replace(config, verification_policy=policy)
    try:
        result = execute_flow_fn(manifest, config=config)
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


def replay_run(args: argparse.Namespace, *, json_output: bool) -> None:
    """Replay a persisted runtime run."""
    manifest = load_manifest(Path(args.manifest))
    policy = load_policy(Path(args.policy))
    planner = ExecutionPlanner()
    resolved_flow = planner.resolve(manifest)
    read_store = DuckDBExecutionReadStore(Path(args.db_path))
    write_store = DuckDBExecutionWriteStore(Path(args.db_path))
    config = ExecutionConfig(
        mode=config_mode_for_replay(),
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
        if result.trace is None:
            raise ValueError("replay result is missing a trace")
        payload = {
            "diff": normalize_for_json(diff, normalize_timestamps=True),
            "trace": normalize_for_json(
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
    print(f"Replay clean: run_id={result.run_id}")


def config_mode_for_replay() -> RunMode:
    """Return the persisted replay execution mode."""
    return RunMode.LIVE


__all__ = [
    "EXIT_CONTRACT_VIOLATION",
    "EXIT_FAILURE",
    "config_mode_for_replay",
    "execute_manifest_command",
    "execute_manifest_command_with_runner",
    "replay_run",
]
