# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

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


def test_cli_run_and_verify_smoke(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    spec_path = tmp_path / "spec.json"
    spec_obj = {
        "description": "cli smoke",
        "constraints": {"x": 1},
        "expected": {},
        "version": 1,
    }
    spec_path.write_text(canonical_dumps(spec_obj) + "\n", encoding="utf-8")

    p = _run(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "run",
            "--spec",
            str(spec_path),
            "--seed",
            "42",
            "--preset",
            "default",
            "--artifacts-dir",
            str(artifacts),
        ]
    )
    assert p.returncode == 0, f"stdout={p.stdout}\nstderr={p.stderr}"
    run_dir = Path(p.stdout.strip())
    assert run_dir.exists()

    assert (run_dir / "spec.json").exists()
    assert (run_dir / "plan.json").exists()
    assert (run_dir / "trace.jsonl").exists()
    assert (run_dir / "verify.json").exists()
    assert (run_dir / "fingerprint.txt").exists()
    assert (run_dir / "run_meta.json").exists()
    verify_contents = (run_dir / "verify.json").read_text(encoding="utf-8")
    assert '"checks_total"' in verify_contents

    p2 = _run(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "verify",
            "--trace",
            str(run_dir / "trace.jsonl"),
            "--plan",
            str(run_dir / "plan.json"),
        ]
    )
    assert p2.returncode == 0, f"stdout={p2.stdout}\nstderr={p2.stderr}"
