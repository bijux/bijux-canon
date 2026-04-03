"""Ensure no generated files are committed."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_no_generated_files_tracked() -> None:
    """Fail if git reports generated artifacts under version control."""
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "check_no_generated_files.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
