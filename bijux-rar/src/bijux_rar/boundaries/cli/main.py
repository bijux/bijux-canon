# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# pyright: reportMissingImports=false
from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn, no_type_check

import typer

from bijux_rar.boundaries.serde.json_file import read_json_file, write_json_file
from bijux_rar.boundaries.serde.trace_jsonl import read_trace_jsonl
from bijux_rar.core.rar_types import Plan, ProblemSpec
from bijux_rar.rar.eval.suite import run_eval_suite
from bijux_rar.rar.skeleton.run_builder import RunArtifacts, RunBuilder, RunInputs
from bijux_rar.rar.traces.replay import replay_from_artifacts
from bijux_rar.rar.verification.verifier import verify_trace

app = typer.Typer(
    add_completion=False,
    help="bijux-rar: deterministic CLI + artifacts + verification gates.",
)

SPEC_PATH_OPTION = typer.Option(
    ..., "--spec", exists=True, dir_okay=False, help="Path to ProblemSpec JSON."
)
PRESET_OPTION = typer.Option("default", "--preset", help="Pipeline preset name.")
SEED_OPTION = typer.Option(0, "--seed", help="Deterministic seed.")
ARTIFACTS_DIR_OPTION = typer.Option(
    Path("artifacts"), "--artifacts-dir", help="Base artifacts directory."
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
    if msg:
        typer.echo(msg, err=(code != 0))
    raise typer.Exit(code=code)


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
    raw = read_json_file(spec)
    spec_obj = ProblemSpec.model_validate(raw)

    inputs = RunInputs(spec=spec_obj, preset=preset, seed=seed)
    builder = RunBuilder()
    arts: RunArtifacts = builder.build(inputs=inputs, artifacts_root=artifacts_dir)
    trace_id = arts.trace.id
    if trace_id is None:
        _exit(2, "run failed: trace id missing (invariant violation)")

    report = arts.verify_report
    if report.failures and fail_on_verify:
        _exit(
            2,
            f"run failed verification ({len(report.failures)} issues). see: {arts.verify_path}",
        )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "run_dir": str(arts.run_dir),
                    "verify_failures": len(report.failures),
                    "summary": report.summary_metrics,
                },
                sort_keys=True,
            )
        )
        _exit(0)

    typer.echo(str(arts.run_dir))
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
    tr = read_trace_jsonl(trace)
    trace_id = tr.id
    if trace_id is None:
        _exit(2, "verification failed: trace id missing (invariant violation)")

    pl_raw = read_json_file(plan)
    pl = Plan.model_validate(pl_raw)

    report = verify_trace(trace=tr, plan=pl, artifacts_dir=trace.parent)

    out = trace.parent / "verify.verify.json"
    write_json_file(out, report.model_dump(mode="json"))

    if report.failures and fail_on_verify:
        _exit(2, f"verification failed ({len(report.failures)} issues). see: {out}")

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "status": "ok" if not report.failures else "failed",
                    "failures": [f.message for f in report.failures],
                    "checks": [c.model_dump(mode="json") for c in report.checks],
                },
                sort_keys=True,
            )
        )
        _exit(0 if not report.failures else 2)

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
    res, replay_trace = replay_from_artifacts(trace)
    payload = {
        "original_trace_fingerprint": res.original_trace_fingerprint,
        "replayed_trace_fingerprint": res.replayed_trace_fingerprint,
        "diff_summary": res.diff_summary,
        "replay_trace_path": str(trace.parent / "replay" / "trace.jsonl"),
    }
    # Compatibility keys expected by tests
    payload["original_fingerprint"] = payload["original_trace_fingerprint"]
    payload["replayed_fingerprint"] = payload["replayed_trace_fingerprint"]
    payload["diff"] = payload["diff_summary"]
    typer.echo(json.dumps(payload, sort_keys=True))

    if (
        fail_on_diff
        and res.original_trace_fingerprint != res.replayed_trace_fingerprint
    ):
        _exit(
            2,
            "replay mismatch: fingerprints differ. "
            f"Replay trace: {payload['replay_trace_path']}. Diff: {res.diff_summary}",
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
    res, out_path = run_eval_suite(
        suite=suite, artifacts_dir=artifacts_dir, preset=preset, seed=seed
    )
    payload = {"summary": str(out_path), **res.to_json()}
    typer.echo(
        json.dumps(
            payload if json_output else {"summary": str(out_path)}, sort_keys=True
        )
    )
    if res.failed:
        _exit(2, f"eval failed ({res.failed}/{res.total} cases). see: {out_path}")
    _exit(0)
