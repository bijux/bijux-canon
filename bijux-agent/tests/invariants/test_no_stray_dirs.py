"""Ensure tests only produce approved directories."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_no_stray_directories_post_test() -> None:
    """Fail if git reports any untracked directories besides allowed ones."""
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "check_no_stray_dirs.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
