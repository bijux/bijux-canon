from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


def test_pipeline_mypy_has_no_regressions() -> None:
    """Ensure the focused mypy scope stays green."""

    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parents[1]
    cache_dir = repo_root / "artifacts" / "bijux-canon-agent" / "test" / ".mypy_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(  # noqa: S603 - executes local mypy for regression coverage
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(repo_root / "configs" / "mypy.ini"),
            "--cache-dir",
            str(cache_dir),
            "src/bijux_canon_agent/pipeline",
            "src/bijux_canon_agent/tracing",
            "src/bijux_canon_agent/models",
            "src/bijux_canon_agent/schema",
            "src/bijux_canon_agent/agents/base.py",
        ],
        capture_output=True,
        text=True,
        cwd=package_root,
    )
    if completed.returncode != 0:
        pytest.fail(
            "Mypy regression detected:\n"
            f"{completed.stdout}\n{completed.stderr}\n"
            "Check configs/mypy.ini and the focused mypy targets if this is intentional."
        )
