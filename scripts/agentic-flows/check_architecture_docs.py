# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "agentic-flows"


def main() -> int:
    invariants = PACKAGE_ROOT / "docs" / "architecture" / "invariants.md"
    if not invariants.exists():
        print("Missing invariants: docs/architecture/invariants.md", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
