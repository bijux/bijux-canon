# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path


CLI = [sys.executable, "-m", "bijux_vex.boundaries.cli.app"]


def run_cmd(args, env):
    return subprocess.check_output(CLI + args, text=True, env=env).strip()


def test_cli_outputs_are_deterministic(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "cli.sqlite"
    env = os.environ.copy()
    env["BIJUX_VEX_STATE_PATH"] = str(db_path)
    monkeypatch.chdir(tmp_path)

    vec = json.dumps([0.0, 0.0])
    run_cmd(
        ["ingest", "--doc", "hello", "--vector", vec, "--vector-store", "memory"],
        env=env,
    )
    run_cmd(
        [
            "materialize",
            "--execution-contract",
            "deterministic",
            "--vector-store",
            "memory",
        ],
        env=env,
    )

    search1 = run_cmd(
        [
            "execute",
            "--vector",
            vec,
            "--execution-contract",
            "deterministic",
            "--execution-intent",
            "exact_validation",
            "--vector-store",
            "memory",
            "--correlation-id",
            "req-1",
        ],
        env=env,
    )
    search2 = run_cmd(
        [
            "execute",
            "--vector",
            vec,
            "--execution-contract",
            "deterministic",
            "--execution-intent",
            "exact_validation",
            "--vector-store",
            "memory",
            "--correlation-id",
            "req-1",
        ],
        env=env,
    )
    assert search1 == search2

    results = json.loads(search1)["results"]
    assert results
    first = results[0]

    explain1 = run_cmd(["explain", "--result-id", first], env=env)
    explain2 = run_cmd(["explain", "--result-id", first], env=env)
    assert explain1 == explain2

    replay1 = run_cmd(["replay", "--request-text", "hello"], env=env)
    replay2 = run_cmd(["replay", "--request-text", "hello"], env=env)
    assert replay1 == replay2
