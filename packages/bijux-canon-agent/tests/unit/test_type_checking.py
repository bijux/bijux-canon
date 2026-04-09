from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest


def _python_has_mypy(python_executable: str) -> bool:
    completed = subprocess.run(
        [
            python_executable,
            "-c",
            "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mypy') else 1)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _resolve_mypy_python(package_root: Path) -> str:
    venv_python = package_root / ".venv" / "bin" / "python"
    if venv_python.is_file() and _python_has_mypy(str(venv_python)):
        return str(venv_python)
    if _python_has_mypy(sys.executable):
        return sys.executable
    return sys.executable


def test_pipeline_mypy_has_no_regressions() -> None:
    """Ensure the focused mypy scope stays green."""

    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parents[1]
    cache_dir = repo_root / "artifacts" / "bijux-canon-agent" / "test" / ".mypy_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    mypy_python = _resolve_mypy_python(package_root)
    completed = subprocess.run(  # noqa: S603 - executes local mypy for regression coverage
        [
            mypy_python,
            "-m",
            "mypy",
            "--config-file",
            str(repo_root / "configs" / "mypy.ini"),
            "--cache-dir",
            str(cache_dir),
            "--follow-imports=silent",
            "src/bijux_canon_agent/contracts",
            "src/bijux_canon_agent/pipeline",
            "src/bijux_canon_agent/traces",
            "src/bijux_canon_agent/llm",
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
