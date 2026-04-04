# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import subprocess


def test_no_generated_files_are_tracked() -> None:
    package_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        ["git", "ls-files", str(package_root)],
        capture_output=True,
        check=True,
        cwd=package_root,
        text=True,
    )
    tracked_paths = [
        Path(line) for line in completed.stdout.splitlines() if line.strip()
    ]
    forbidden_markers = {
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }

    offenders = [
        path
        for path in tracked_paths
        if any(part in forbidden_markers for part in path.parts)
        or path.suffix in {".pyc", ".pyo"}
    ]

    assert offenders == []
