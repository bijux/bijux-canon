# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    path = Path("docs/architecture/design_debt.md")
    if not path.exists():
        print(
            "Missing design debt ledger: docs/architecture/design_debt.md",
            file=sys.stderr,
        )
        return 1
    items = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped)
    if len(items) > 10:
        print("Design debt ledger exceeds 10 items.", file=sys.stderr)
        return 1
    for item in items:
        if "why:" not in item or "exit:" not in item:
            print(
                "Design debt items must include why: and exit: fields.",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
