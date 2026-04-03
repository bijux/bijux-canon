# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Directories that should never be considered "root pollution"
DEFAULT_EXCLUDES = {
    ".git",
    ".tox",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".pyright",
    ".ruff_cache",
    ".idea",
    "TODO",
    "artifacts",
}

MAX_HASH_BYTES = 5 * 1024 * 1024  # 5 MB


@dataclass(frozen=True)
class FileSig:
    size: int
    sha256: str | None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path, excludes: set[str]) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories
        rel_dir = Path(dirpath).relative_to(root)
        parts = set(rel_dir.parts)
        if parts & excludes:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in excludes]

        for fn in filenames:
            p = Path(dirpath) / fn
            rel = p.relative_to(root)
            if rel.parts and rel.parts[0] in excludes:
                continue
            yield p


def snapshot(root: Path, excludes: set[str]) -> dict[str, FileSig]:
    out: dict[str, FileSig] = {}
    for p in iter_files(root, excludes):
        rel = p.relative_to(root).as_posix()
        size = p.stat().st_size
        digest = None
        if size <= MAX_HASH_BYTES:
            digest = sha256_file(p)
        out[rel] = FileSig(size=size, sha256=digest)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()

    root = Path(args.root).resolve()
    excludes = set(DEFAULT_EXCLUDES) | set(args.exclude)

    snap = snapshot(root, excludes)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(
            {k: {"size": v.size, "sha256": v.sha256} for k, v in sorted(snap.items())},
            f,
            indent=2,
            sort_keys=True,
        )


if __name__ == "__main__":
    main()
