from __future__ import annotations

import subprocess
from pathlib import Path


PATTERNS = ("__pycache__", ".pyc", ".coverage", ".mypy_cache", ".ruff_cache")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root(),
    )
    offenders = [path for path in result.stdout.splitlines() if any(pattern in path for pattern in PATTERNS)]
    if offenders:
        print("error: generated artifacts are tracked in git:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
