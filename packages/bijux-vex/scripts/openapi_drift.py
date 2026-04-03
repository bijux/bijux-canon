#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

"""OpenAPI drift detector for bijux-vex execution surface."""


import argparse
import json
from pathlib import Path
import sys

from bijux_vex.core.canon import canon
from bijux_vex.core.identity.ids import fingerprint


def load_spec(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected", type=Path, default=Path("artifacts/api/expected.json")
    )
    parser.add_argument(
        "--actual", type=Path, default=Path("artifacts/api/current.json")
    )
    parser.add_argument("--mode", choices=["check", "print"], default="check")
    args = parser.parse_args()

    expected = load_spec(args.expected)
    actual = load_spec(args.actual)

    if not expected or not actual:
        print("OpenAPI specs missing; skipping drift check.", file=sys.stderr)
        return 0

    if args.mode == "print":
        print(json.dumps(actual, indent=2))
        return 0

    if fingerprint(expected) != fingerprint(actual):
        print("OpenAPI drift detected", file=sys.stderr)
        return 1
    print("OpenAPI specs match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
