#!/usr/bin/env python3
"""Verify installed dependencies against an allowlist if present."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _read_allowlist(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    allowlist_path = repo_root / "config" / "dependency_allowlist.txt"
    if not allowlist_path.exists():
        print("No dependency allowlist found; skipping")
        return 0

    allowlist = _read_allowlist(allowlist_path)
    if not allowlist:
        print("Dependency allowlist is empty; skipping")
        return 0

    result = subprocess.run(
        ["python", "-m", "pip", "freeze"],
        check=False,
        capture_output=True,
        text=True,
    )
    installed = {
        line.split("==")[0] for line in result.stdout.splitlines() if "==" in line
    }
    extras = sorted(installed - allowlist)
    if extras:
        print("Dependencies not in allowlist:")
        for name in extras:
            print(f"  - {name}")
        return 1

    print("✔ Dependency allowlist satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
