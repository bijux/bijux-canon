# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


CLI = [sys.executable, "-m", "bijux_vex.boundaries.cli.app"]


def run_cmd(args):
    return subprocess.check_output(CLI + args, text=True).strip()


def test_basic_cli_flow(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vec = json.dumps([0.0, 0.0])
    out = run_cmd(
        ["ingest", "--doc", "hello", "--vector", vec, "--vector-store", "memory"]
    )
    assert json.loads(out)["ingested"] == 1

    out = run_cmd(
        [
            "materialize",
            "--execution-contract",
            "deterministic",
            "--vector-store",
            "memory",
        ]
    )
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
            "--vector-store",
            "memory",
        ]
    )
    res = json.loads(out)["results"]
    assert len(res) >= 1

    first_vector_id = res[0]
    out = run_cmd(["explain", "--result-id", first_vector_id])
    exp = json.loads(out)
    assert exp["vector_id"] == first_vector_id

    out = run_cmd(["replay", "--request-text", "hello"])
    rep = json.loads(out)
    assert rep["matches"] is True
