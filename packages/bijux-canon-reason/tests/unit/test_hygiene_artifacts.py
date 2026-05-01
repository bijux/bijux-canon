# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path


def test_no_root_coverage_or_benchmark() -> None:
    # Resolve repository root relative to this test file to avoid cwd surprises.
    root = Path(__file__).resolve().parents[2]
    forbidden = [root / ".coveragerc", root / ".benchmarks"]
    # Managed artifact aliases are symlinks and are allowed.
    existing = [p for p in forbidden if p.exists() and not p.is_symlink()]
    if existing:
        raise AssertionError(f"forbidden artifacts in repo root: {existing}")
