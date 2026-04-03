# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path


def test_unit_tests_mirror_top_level_source_areas() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src" / "bijux_canon_ingest"
    tests_root = package_root / "tests" / "unit"

    src_dirs = {
        path.name
        for path in src_root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    test_dirs = {path.name for path in tests_root.iterdir() if path.is_dir()}

    missing = src_dirs - test_dirs
    assert missing == set()
