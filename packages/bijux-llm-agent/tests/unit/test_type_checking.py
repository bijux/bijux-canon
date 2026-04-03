from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


def test_pipeline_mypy_has_no_regressions() -> None:
    """Ensure the focused mypy scope stays green."""

    repo_root = Path(__file__).resolve().parents[2]
    cache_dir = repo_root / "artifacts" / "test" / ".mypy_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(  # noqa: S603 - executes local mypy for regression coverage
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            "../../configs/mypy.ini",
            "--cache-dir",
            str(cache_dir),
            "src/bijux_agent/pipeline",
            "src/bijux_agent/tracing",
            "src/bijux_agent/models",
            "src/bijux_agent/schema",
            "src/bijux_agent/agents/base.py",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if completed.returncode != 0:
        pytest.fail(
            "Mypy regression detected:\n"
            f"{completed.stdout}\n"
            "Check ../../configs/mypy.ini and the focused mypy targets if this is intentional."
        )
