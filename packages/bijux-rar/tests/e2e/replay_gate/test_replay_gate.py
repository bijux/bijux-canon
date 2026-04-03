# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path
import os
import subprocess
import sys

from bijux_rar.core.fingerprints import canonical_dumps


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[3]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + (
        os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
    )
    return subprocess.run(  # noqa: S603
        cmd, text=True, capture_output=True, check=True, env=env
    )


def test_replay_gate_same_spec_seed_same_fingerprint(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    spec_path = tmp_path / "spec.json"
    spec_obj = {
        "description": "replay gate",
        "constraints": {},
        "expected": {},
        "version": 1,
    }
    spec_path.write_text(canonical_dumps(spec_obj) + "\n", encoding="utf-8")

    def run_once() -> Path:
        p = _run(
            [
                sys.executable,
                "-m",
                "bijux_rar",
                "run",
                "--spec",
                str(spec_path),
                "--seed",
                "7",
                "--preset",
                "default",
                "--artifacts-dir",
                str(artifacts),
            ]
        )
        assert p.returncode == 0, f"stdout={p.stdout}\nstderr={p.stderr}"
        return Path(p.stdout.strip())

    run_dir_1 = run_once()
    run_dir_2 = run_once()

    fp1 = (run_dir_1 / "fingerprint.txt").read_text(encoding="utf-8").strip()
    fp2 = (run_dir_2 / "fingerprint.txt").read_text(encoding="utf-8").strip()

    assert fp1 == fp2

    replay = _run(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "replay",
            "--trace",
            str(run_dir_1 / "trace.jsonl"),
        ]
    )
    assert replay.returncode == 0, f"stdout={replay.stdout}\nstderr={replay.stderr}"
    payload = json.loads(replay.stdout)
    assert payload["original_fingerprint"] == payload["replayed_fingerprint"], (
        f"diff={payload.get('diff')}"
    )
