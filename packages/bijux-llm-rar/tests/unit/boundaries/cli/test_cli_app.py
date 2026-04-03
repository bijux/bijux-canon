# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bijux_rar.boundaries.cli.main import app
from bijux_rar.core.fingerprints import canonical_dumps

runner = CliRunner()


def test_cli_run_verify_replay(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    spec_path = tmp_path / "spec.json"
    spec = {"description": "cli unit", "constraints": {}, "expected": {}, "version": 1}
    spec_path.write_text(canonical_dumps(spec) + "\n", encoding="utf-8")

    res_run = runner.invoke(
        app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "1",
            "--preset",
            "default",
            "--artifacts-dir",
            str(artifacts),
        ],
    )
    assert res_run.exit_code == 0, res_run.stderr
    run_dir = Path(res_run.stdout.strip())
    assert run_dir.exists()

    res_verify = runner.invoke(
        app,
        [
            "verify",
            "--trace",
            str(run_dir / "trace.jsonl"),
            "--plan",
            str(run_dir / "plan.json"),
        ],
    )
    assert res_verify.exit_code == 0, res_verify.stderr

    res_replay = runner.invoke(
        app,
        [
            "replay",
            "--trace",
            str(run_dir / "trace.jsonl"),
        ],
    )
    assert res_replay.exit_code == 0, res_replay.stderr
    payload = json.loads(res_replay.stdout.strip())
    assert payload["original_fingerprint"] == payload["replayed_fingerprint"]


def test_main_import_executes() -> None:
    # Ensure __main__ module imports without side effects
    import importlib

    importlib.import_module("bijux_rar.__main__")
    from bijux_rar.rar.skeleton.fake_runtime import FakeRuntime

    assert FakeRuntime(seed=1).seed == 1
