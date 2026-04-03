#!/usr/bin/env python3
"""Fail when generated artifacts are accidentally tracked in git."""

from __future__ import annotations

import subprocess
import sys


PATTERNS = ("__pycache__", ".pyc", ".coverage", ".mypy_cache", ".ruff_cache")


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=False,
    )
    tracked = result.stdout.splitlines()
    offenders = [
        path for path in tracked if any(pattern in path for pattern in PATTERNS)
    ]
    if offenders:
        print("error: generated artifacts are tracked in git:")
        for path in offenders:
            print(f"  - {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
