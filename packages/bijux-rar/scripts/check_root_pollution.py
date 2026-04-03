# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ruff: disable=E402
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_repo import DEFAULT_EXCLUDES, snapshot  # noqa: E402


def load_snapshot(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()

    root = Path(args.root).resolve()
    excludes = set(DEFAULT_EXCLUDES) | set(args.exclude)

    before_path = Path(args.before)
    before = load_snapshot(before_path)
    after_snap = snapshot(root, excludes)
    after = {k: {"size": v.size, "sha256": v.sha256} for k, v in after_snap.items()}

    before_keys = set(before.keys())
    after_keys = set(after.keys())

    added = sorted(after_keys - before_keys)
    removed = sorted(before_keys - after_keys)

    changed = []
    for k in sorted(before_keys & after_keys):
        if before[k] != after[k]:
            changed.append(k)

    pycache_dirs = [
        str(p.relative_to(root))
        for p in root.rglob("__pycache__")
        if not set(p.relative_to(root).parts) & excludes
    ]

    if added or removed or changed:
        msg = [
            "Root pollution detected (changes outside artifacts/ and allowed caches):"
        ]
        if added:
            msg.append(f"  Added ({len(added)}):")
            msg.extend([f"    + {p}" for p in added])
        if removed:
            msg.append(f"  Removed ({len(removed)}):")
            msg.extend([f"    - {p}" for p in removed])
        if changed:
            msg.append(f"  Modified ({len(changed)}):")
            msg.extend([f"    * {p}" for p in changed])
        raise SystemExit("\n".join(msg))

    if pycache_dirs:
        msg = ["__pycache__ directories detected (should be cleaned):"]
        msg.extend([f"  - {p}" for p in sorted(pycache_dirs)])
        raise SystemExit("\n".join(msg))


if __name__ == "__main__":
    main()
