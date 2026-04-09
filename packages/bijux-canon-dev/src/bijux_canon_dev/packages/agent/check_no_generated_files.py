"""Check no generated files helpers."""

from __future__ import annotations

from pathlib import Path
import shutil

from bijux_canon_dev.trusted_process import run_text

PATTERNS = ("__pycache__", ".pyc", ".coverage", ".mypy_cache", ".ruff_cache")


def repo_root() -> Path:
    """Handle repo root."""
    return Path(__file__).resolve().parents[6]


def git_executable() -> str:
    """Handle Git executable."""
    resolved = shutil.which("git")
    if resolved is None:
        raise SystemExit("git executable not found")
    return resolved


def main() -> int:
    """Run the command-line entry point."""
    result = run_text(
        [git_executable(), "ls-files"],
        capture_output=True,
        check=False,
        cwd=repo_root(),
    )
    offenders = [
        path
        for path in result.stdout.splitlines()
        if any(pattern in path for pattern in PATTERNS)
    ]
    if offenders:
        print("error: generated artifacts are tracked in git:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
