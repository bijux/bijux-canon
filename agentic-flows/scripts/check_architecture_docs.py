# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    invariants = Path("docs/architecture/invariants.md")
    if not invariants.exists():
        print("Missing invariants: docs/architecture/invariants.md", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
