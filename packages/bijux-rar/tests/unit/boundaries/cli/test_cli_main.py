# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bijux_rar.boundaries.cli import app as root_app

runner = CliRunner()


def _write_spec(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "description": "Return 2+2",
                "constraints": {},
                "expected_output_type": "Claim",
                "version": 1,
            }
        ),
        encoding="utf-8",
    )


def test_run_verify_replay_json(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.json"
    artifacts_dir = tmp_path / "artifacts"
    _write_spec(spec_path)

    # run with JSON output
    res_run = runner.invoke(
        root_app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--artifacts-dir",
            str(artifacts_dir),
            "--json",
        ],
    )
    assert res_run.exit_code == 0
    payload = json.loads(res_run.stdout)
    run_dir = Path(payload["run_dir"])
    assert run_dir.exists()

    # verify with JSON output
    res_ver = runner.invoke(
        root_app,
        [
            "verify",
            "--trace",
            str(run_dir / "trace.jsonl"),
            "--plan",
            str(run_dir / "plan.json"),
            "--json",
        ],
    )
    assert res_ver.exit_code == 0
    ver_payload = json.loads(res_ver.stdout)
    assert ver_payload["status"] == "ok"

    # replay with JSON output
    res_rep = runner.invoke(
        root_app,
        [
            "replay",
            "--trace",
            str(run_dir / "trace.jsonl"),
            "--json",
        ],
    )
    assert res_rep.exit_code == 0
    rep_payload = json.loads(res_rep.stdout)
    assert rep_payload["original_trace_fingerprint"] == rep_payload[
        "replayed_trace_fingerprint"
    ]


def test_eval_json_output(tmp_path: Path) -> None:
    res = runner.invoke(
        root_app,
        [
            "eval",
            "--suite",
            "small",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert "summary" in payload
