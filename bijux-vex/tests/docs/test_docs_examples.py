# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import doctest
import os
from pathlib import Path
import subprocess
import sys


def _env(repo_root: Path, tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    python_bin = str(repo_root / ".venv" / "bin" / "python")
    env["PYTHONPATH"] = f"{repo_root / 'src'}:{env.get('PYTHONPATH', '')}"
    env["BIJUX_VEX_STATE_PATH"] = str(tmp_path / "session.sqlite")
    env["BIJUX_VEX_RUN_DIR"] = str(tmp_path / "runs")
    env["PYTHON_BIN"] = python_bin
    env["PATH"] = f"{repo_root / '.venv' / 'bin'}:{env.get('PATH', '')}"
    return env


def test_determinism_doc_snippets():
    repo_root = Path(__file__).resolve().parents[2]
    doc_path = repo_root / "docs" / "design" / "determinism.md"
    text = doc_path.read_text(encoding="utf-8")
    parser = doctest.DocTestParser()
    test = parser.get_doctest(
        text, {}, name=str(doc_path), filename=str(doc_path), lineno=0
    )
    runner = doctest.DocTestRunner(verbose=False)
    failures, _ = runner.run(test)
    assert failures == 0


def test_readme_quickstart(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = _env(repo_root, tmp_path)
    cmd = [
        sys.executable,
        "-m",
        "bijux_vex.boundaries.cli.app",
        "ingest",
        "--doc",
        "hello",
        "--vector",
        "[0,1,0]",
        "--vector-store",
        "memory",
    ]
    subprocess.run(cmd, env=env, cwd=repo_root, check=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "bijux_vex.boundaries.cli.app",
            "materialize",
            "--execution-contract",
            "deterministic",
            "--vector-store",
            "memory",
        ],
        env=env,
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "bijux_vex.boundaries.cli.app",
            "execute",
            "--vector",
            "[0,1,0]",
            "--execution-contract",
            "deterministic",
            "--execution-intent",
            "exact_validation",
            "--vector-store",
            "memory",
        ],
        env=env,
        cwd=repo_root,
        check=True,
    )


def test_workflow_scripts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = _env(repo_root, tmp_path)
    scripts = [
        repo_root / "docs" / "examples" / "workflows" / "workflow_a.sh",
        repo_root / "docs" / "examples" / "workflows" / "workflow_b.sh",
        repo_root / "docs" / "examples" / "workflows" / "workflow_c.sh",
    ]
    for script in scripts:
        subprocess.run(["bash", str(script)], env=env, cwd=repo_root, check=True)


def test_demo_app_script(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = _env(repo_root, tmp_path)
    subprocess.run(
        [sys.executable, "docs/examples/demo_app.py"],
        env=env,
        cwd=repo_root,
        check=True,
    )
