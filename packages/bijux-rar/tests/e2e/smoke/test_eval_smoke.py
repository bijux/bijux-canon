# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

from bijux_rar.core.fingerprints import canonical_dumps


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[3]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + (
        os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else ""
    )
    return subprocess.run(  # noqa: S603
        cmd,
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )


def test_cli_eval_smoke(tmp_path: Path) -> None:
    # Create a disposable suite rooted at CWD, as expected by the eval runner.
    suite_dir = tmp_path / "eval" / "suites" / "t1"
    suite_dir.mkdir(parents=True, exist_ok=True)

    problems = [
        {
            "description": "Compute 1+1.",
            "constraints": {"domain": "arithmetic"},
            "expected_output_type": "Claim",
            "version": 1,
        }
    ]
    (suite_dir / "problems.jsonl").write_text(
        "\n".join(canonical_dumps(p) for p in problems) + "\n",
        encoding="utf-8",
    )

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    p = _run(
        [
            sys.executable,
            "-m",
            "bijux_rar",
            "eval",
            "--suite",
            "t1",
            "--artifacts-dir",
            str(artifacts),
        ],
        cwd=tmp_path,
    )
    assert p.returncode in (0, 2), f"stdout={p.stdout}\nstderr={p.stderr}"
    # summary.json must always be produced.
    assert (artifacts / "eval" / "t1" / "summary.json").exists()
