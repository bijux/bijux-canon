"""Ensure no generated files are committed."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_no_generated_files_tracked() -> None:
    """Fail if git reports generated artifacts under version control."""
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "packages" / "bijux-canon-dev" / "src")
    completed = subprocess.run(  # noqa: S603 - invokes a checked-in test helper
        [
            sys.executable,
            "-m",
            "bijux_canon_dev.packages.agent.check_no_generated_files",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=package_root,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
