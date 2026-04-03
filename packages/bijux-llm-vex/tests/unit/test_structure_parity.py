# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from pathlib import Path


def test_src_tests_directory_parity():
    src_root = Path(__file__).parents[2] / "src" / "bijux_vex"
    tests_root = Path(__file__).parents[1] / "unit"
    src_dirs = {
        p.relative_to(src_root).parts[0]
        for p in src_root.iterdir()
        if p.is_dir()
        if p.name != "__pycache__"
    }
    test_dirs = {p.name for p in tests_root.iterdir() if p.is_dir()}
    missing = src_dirs - test_dirs
    assert not missing, f"Missing test mirrors for: {', '.join(sorted(missing))}"
