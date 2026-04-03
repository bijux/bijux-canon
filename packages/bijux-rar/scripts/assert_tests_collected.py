# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import re
import subprocess
import sys


def main() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only"],
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")

    m = re.search(r"collected\s+(\d+)\s+items?", out)
    if not m:
        # If pytest output format changes, fail hard: no silent green.
        print(out)
        raise SystemExit(
            "Could not determine number of collected tests from pytest output."
        )

    n = int(m.group(1))
    if n <= 0:
        print(out)
        raise SystemExit("No tests collected (must be > 0).")

    if proc.returncode != 0:
        print(out)
        raise SystemExit(f"pytest --collect-only failed with code {proc.returncode}.")


if __name__ == "__main__":
    main()
