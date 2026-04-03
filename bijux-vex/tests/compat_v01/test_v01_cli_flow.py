# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


CLI = [sys.executable, "-m", "bijux_vex.boundaries.cli.app"]


def run_cmd(args):
    return subprocess.check_output(CLI + args, text=True).strip()


def test_v01_cli_flow(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vec = json.dumps([0.0, 0.0])
    out = run_cmd(["ingest", "--doc", "hello", "--vector", vec])
    assert json.loads(out)["ingested"] == 1

    out = run_cmd(["materialize", "--execution-contract", "deterministic"])
    assert json.loads(out)["artifact_id"] == "art-1"

    out = run_cmd(
        [
            "execute",
            "--vector",
            vec,
            "--execution-contract",
            "deterministic",
            "--execution-intent",
            "exact_validation",
        ]
    )
    res = json.loads(out)["results"]
    assert len(res) >= 1
