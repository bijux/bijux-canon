"""Ensure tests only produce approved directories."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_no_stray_directories_post_test() -> None:
    """Fail if git reports any untracked directories besides allowed ones."""
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parents[1]
    script = repo_root / "scripts" / "bijux-canon-agent" / "check_no_stray_dirs.py"
    completed = subprocess.run(  # noqa: S603 - invokes a checked-in test helper
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=package_root,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
