# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path


def test_no_root_coverage_or_benchmark() -> None:
    # Resolve repository root relative to this test file to avoid cwd surprises.
    root = Path(__file__).resolve().parents[2]
    forbidden = [root / ".coveragerc", root / ".benchmarks"]
    missing = [p for p in forbidden if not p.exists()]
    # If any exist, fail with a helpful message.
    if len(missing) != len(forbidden):
        existing = [p for p in forbidden if p.exists()]
        raise AssertionError(f"forbidden artifacts in repo root: {existing}")
