#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

"""
Run the conformance suite and emit a simple report.
"""


import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend", default="memory", help="Backend name used for reporting."
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cmd = ["pytest", "tests/conformance"]
    if args.verbose:
        cmd.append("-vv")
    print(f"[conformance] backend={args.backend} :: running {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
