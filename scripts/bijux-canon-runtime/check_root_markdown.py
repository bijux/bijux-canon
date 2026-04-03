# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "bijux-canon-runtime"

ALLOWED = {
    "CHANGELOG.md",
    "README.md",
}


def main() -> int:
    found = sorted(path.name for path in PACKAGE_ROOT.glob("*.md") if path.is_file())
    extras = sorted(name for name in found if name not in ALLOWED)
    if extras:
        print("Root markdown whitelist violation:")
        for name in extras:
            print(f"- {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
