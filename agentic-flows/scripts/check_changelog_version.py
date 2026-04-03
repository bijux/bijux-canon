# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def _parse_version(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return None


def _git_show(path: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"HEAD~1:{path}"], text=True
        ).strip()
    except Exception:
        return None


def main() -> int:
    citation = Path("CITATION.cff")
    changelog = Path("CHANGELOG.md")
    if not citation.exists():
        print("CITATION.cff missing; skipping changelog version check.")
        return 0
    current_version = _parse_version(citation.read_text())
    previous_text = _git_show("CITATION.cff")
    if not previous_text:
        return 0
    previous_version = _parse_version(previous_text)
    if not current_version or not previous_version:
        return 0
    if current_version == previous_version:
        return 0
    try:
        changed_files = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1..HEAD"], text=True
        ).splitlines()
    except Exception:
        return 0
    if str(changelog) not in changed_files:
        print(
            "Version bumped in CITATION.cff without CHANGELOG.md update.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
