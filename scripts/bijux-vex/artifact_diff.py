#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

"""
Compute and compare fingerprints for artifacts.
"""


import argparse
import json
from pathlib import Path
from typing import Any

from bijux_vex.core.canon import canon
from bijux_vex.core.identity.ids import fingerprint


def load(path: Path) -> Any:
    data = path.read_bytes()
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()

    left_obj = load(args.left)
    right_obj = load(args.right)

    left_fp = fingerprint(left_obj)
    right_fp = fingerprint(right_obj)
    print(f"{args.left}: {left_fp}")
    print(f"{args.right}: {right_fp}")

    if left_fp != right_fp:
        print("Artifacts differ.")
        return 1
    print("Artifacts match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
