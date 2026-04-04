# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path


def test_no_generated_directories_exist_under_package_root() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src"

    offenders = sorted(
        path.relative_to(package_root).as_posix()
        for path in src_root.rglob("__pycache__")
    )
    offenders.extend(
        sorted(
            name
            for name in (".pytest_cache", ".ruff_cache", ".mypy_cache")
            if (package_root / name).exists()
        )
    )

    assert offenders == []
