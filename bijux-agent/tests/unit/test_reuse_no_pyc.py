"""Ensure REUSE lint never mentions compiled bytecode."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_reuse_no_pyc_references() -> None:
    """Fail if reuse lint reports `.pyc` or `__pycache__` paths."""
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "check_reuse_no_pyc.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
