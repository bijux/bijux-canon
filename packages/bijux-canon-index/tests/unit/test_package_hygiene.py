# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

FORBIDDEN_RUNTIME_FILES = {
    "session.sqlite",
    "embeddings-cache.sqlite",
    "pgvector.sqlite",
}


def test_package_root_has_no_runtime_state_files() -> None:
    package_root = Path(__file__).resolve().parents[2]
    offenders = [
        path.name
        for path in package_root.iterdir()
        if path.is_file() and path.name in FORBIDDEN_RUNTIME_FILES
    ]
    assert not offenders, (
        f"Remove runtime files from package root: {', '.join(sorted(offenders))}"
    )
