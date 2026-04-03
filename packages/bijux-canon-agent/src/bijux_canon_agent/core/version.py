"""Runtime version resolution helpers."""

# ruff: noqa: S603

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess  # nosec B404 - subprocess is used with fixed git arguments


def _git_executable() -> str | None:
    return shutil.which("git")


def _describe_tag(repo_root: Path) -> str | None:
    git_exec = _git_executable()
    if not git_exec:
        return None
    try:
        result = subprocess.run(  # nosec S603
            [git_exec, "describe", "--tags", "--exact-match"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip()


def _rev_parse_short(repo_root: Path) -> str | None:
    git_exec = _git_executable()
    if not git_exec:
        return None
    try:
        result = subprocess.run(  # nosec S603
            [git_exec, "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except subprocess.CalledProcessError:
        return None
    return result.stdout.strip()


def get_runtime_version() -> str:
    """Resolve the runtime version from git tags or commit hash."""

    repo_root = Path(__file__).resolve().parents[4]
    tag = _describe_tag(repo_root)
    if tag:
        return tag
    short_hash = _rev_parse_short(repo_root)
    if short_hash:
        return f"dev+{short_hash}"
    return "dev+unknown"
