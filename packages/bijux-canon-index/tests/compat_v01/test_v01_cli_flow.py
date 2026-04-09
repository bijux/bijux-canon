# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

CLI = [sys.executable, "-m", "bijux_canon_index.interfaces.cli.app"]


def run_cmd(args):
    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    return subprocess.check_output(CLI + args, text=True, env=env).strip()


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
