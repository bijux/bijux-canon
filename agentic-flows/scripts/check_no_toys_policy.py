# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

REQUIRED_PHRASES = (
    "This doc lists rejected patterns.",
    "Anti-patterns align with [Core](core.md).",
    "Hidden stochastic paths violate [Invariants](../architecture/invariants.md).",
)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    policy_path = repo_root / "docs" / "governance" / "anti_patterns.md"
    if not policy_path.exists():
        print("Policy doc missing: docs/governance/anti_patterns.md")
        return 1
    contents = policy_path.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in contents]
    if missing:
        print("Policy doc missing required phrases:")
        for phrase in missing:
            print(f"- {phrase}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
