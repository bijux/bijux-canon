#!/usr/bin/env python3
"""Fail if `reuse lint` references `.pyc` or `__pycache__`."""

from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> int:
    if shutil.which("reuse") is None:
        print("reuse executable missing; skipping bytecode check.")
        return 0
    completed = subprocess.run(
        ["reuse", "lint"],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        print("reuse lint failed:", completed.stderr, completed.stdout)
        return completed.returncode
    output = completed.stdout + completed.stderr
    if ".pyc" in output or "__pycache__" in output:
        print("reuse lint references binary/cache artifacts:")
        print(output)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
