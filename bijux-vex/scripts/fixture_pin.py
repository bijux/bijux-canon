#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

"""
Pin fixture files (corpora, vectors, queries) into data/ for deterministic runs.
"""


import argparse
import shutil
from pathlib import Path
from typing import Iterable, Tuple

from bijux_vex.core.identity.ids import fingerprint


def pin_file(source: Path, dest: Path) -> Tuple[Path, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    fp = fingerprint(dest.read_bytes())
    return dest, fp


def process(paths: Iterable[Path], output_dir: Path) -> None:
    for path in paths:
        if not path.exists():
            continue
        dest = output_dir / path.name
        pinned, fp = pin_file(path, dest)
        print(f"Pinned {path} -> {pinned} (fp={fp})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path, help="Fixture files to pin")
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()

    if not args.paths:
        print("No fixtures provided; nothing to pin.")
        return 0

    process(args.paths, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
