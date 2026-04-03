# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

ALLOWED = {
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "README.md",
    "SECURITY.md",
}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    found = sorted(path.name for path in repo_root.glob("*.md") if path.is_file())
    extras = sorted(name for name in found if name not in ALLOWED)
    if extras:
        print("Root markdown whitelist violation:")
        for name in extras:
            print(f"- {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
