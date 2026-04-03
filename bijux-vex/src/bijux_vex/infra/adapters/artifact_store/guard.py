# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Artifact path guard to prevent writes outside artifacts/ unless explicitly allowed.
"""

from __future__ import annotations

from pathlib import Path

from bijux_vex.core.errors import ValidationError

ARTIFACT_ROOT = Path("artifacts").resolve()


def assert_artifact_path(path: Path, *, allow_outside: bool = False) -> Path:
    resolved = path.resolve()
    if allow_outside:
        return resolved
    if ARTIFACT_ROOT not in resolved.parents and resolved != ARTIFACT_ROOT:
        raise ValidationError(f"Write blocked outside artifacts/: {resolved}")
    return resolved


def write_bytes(path: Path, data: bytes, *, allow_outside: bool = False) -> None:
    target = assert_artifact_path(path, allow_outside=allow_outside)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
