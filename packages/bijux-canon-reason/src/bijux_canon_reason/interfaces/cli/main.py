# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Main helpers for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn, no_type_check

import typer

from bijux_canon_reason.application.cli_services import (
    execute_eval_command,
    execute_replay_command,
    execute_run_command,
    execute_verify_command,
)

app = typer.Typer(
    add_completion=False,
    help="bijux-canon-reason: deterministic CLI + artifacts + verification gates.",
)

SPEC_PATH_OPTION = typer.Option(
    ..., "--spec", exists=True, dir_okay=False, help="Path to ProblemSpec JSON."
)
PRESET_OPTION = typer.Option("default", "--preset", help="Pipeline preset name.")
SEED_OPTION = typer.Option(0, "--seed", help="Deterministic seed.")
ARTIFACTS_DIR_OPTION = typer.Option(
    Path("artifacts/bijux-canon-reason"),
    "--artifacts-dir",
    help="Base artifacts directory.",
)
FAIL_ON_VERIFY_OPTION = typer.Option(
    False,
    "--fail-on-verify/--no-fail-on-verify",
    help="Exit non-zero if verify fails.",
)
TRACE_PATH_OPTION = typer.Option(
    ..., "--trace", exists=True, dir_okay=False, help="Path to trace.jsonl"
)
PLAN_PATH_OPTION = typer.Option(
    ...,
    "--plan",
    exists=True,
    dir_okay=False,
    help="Plan JSON required for verification",
)
FAIL_ON_DIFF_OPTION = typer.Option(
    True,
    "--fail-on-diff/--no-fail-on-diff",
    help="Exit non-zero when replay fingerprint differs.",
)
EVAL_SUITE_OPTION = typer.Option(
    "small", "--suite", help="Eval suite name (placeholder until eval suites land)."
)


def _exit(code: int, msg: str | None = None) -> NoReturn:
    """Handle exit."""
    if msg:
        typer.echo(msg, err=(code != 0))
    raise typer.Exit(code=code)


def _emit_json(payload: dict[str, object]) -> None:
    """Handle emit JSON."""
    typer.echo(json.dumps(payload, sort_keys=True))


@app.command()
@no_type_check
def run(
    spec: Path = SPEC_PATH_OPTION,
    preset: str = PRESET_OPTION,
    seed: int = SEED_OPTION,
    artifacts_dir: Path = ARTIFACTS_DIR_OPTION,
    fail_on_verify: bool = FAIL_ON_VERIFY_OPTION,
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON instead of plain output."
    ),
) -> None:
    """Run the requested operation."""
    try:
        result = execute_run_command(
            spec_path=spec,
            preset=preset,
            seed=seed,
            artifacts_dir=artifacts_dir,
        )
    except RuntimeError as exc:
        _exit(2, f"run failed: {exc}")
    if result.failure_count and fail_on_verify:
        _exit(
            2,
            f"run failed verification ({result.failure_count} issues). see: {result.verify_path}",
        )

    if json_output:
        _emit_json(result.payload)
        _exit(0)

    typer.echo(str(result.run_dir))
    _exit(0)


@app.command()
@no_type_check
def verify(
    trace: Path = TRACE_PATH_OPTION,
    plan: Path = PLAN_PATH_OPTION,
    fail_on_verify: bool = FAIL_ON_VERIFY_OPTION,
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON instead of plain output."
    ),
) -> None:
    """Handle verify."""
    try:
        result = execute_verify_command(trace_path=trace, plan_path=plan)
    except RuntimeError as exc:
        _exit(2, f"verification failed: {exc}")
    if result.failure_count and fail_on_verify:
        _exit(
            2,
            f"verification failed ({result.failure_count} issues). see: {result.output_path}",
        )

    if json_output:
        _emit_json(result.payload)
        _exit(0 if not result.failure_count else 2)

    typer.echo("ok")
    _exit(0)


@app.command()
@no_type_check
def replay(
    trace: Path = TRACE_PATH_OPTION,
    fail_on_diff: bool = FAIL_ON_DIFF_OPTION,
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON instead of plain output."
    ),
) -> None:
    """Handle replay."""
    result = execute_replay_command(trace)
    _emit_json(result.payload)

    if fail_on_diff and result.mismatch:
        _exit(
            2,
            "replay mismatch: fingerprints differ. "
            f"Replay trace: {result.payload['replay_trace_path']}. "
            f"Diff: {result.payload['diff_summary']}",
        )

    _exit(0)


@app.command(name="eval")
@no_type_check
def eval_suite(
    suite: str = EVAL_SUITE_OPTION,
    artifacts_dir: Path = ARTIFACTS_DIR_OPTION,
    preset: str = PRESET_OPTION,
    seed: int = SEED_OPTION,
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON instead of plain output."
    ),
) -> None:
    """Handle eval suite."""
    result = execute_eval_command(
        suite=suite,
        artifacts_dir=artifacts_dir,
        preset=preset,
        seed=seed,
    )
    _emit_json(
        result.payload if json_output else {"summary": str(result.summary_path)}
    )
    if result.failed:
        _exit(
            2,
            f"eval failed ({result.failed}/{result.total} cases). "
            f"see: {result.summary_path}",
        )
    _exit(0)
