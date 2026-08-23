# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_ROOTS = tuple(
    REPO_ROOT / "apis" / "bijux-canon-runtime" / version for version in ("v1", "v2")
)


def _extract_version(text: str) -> str:
    in_info = False
    info_indent = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "info:":
            in_info = True
            info_indent = len(line) - len(line.lstrip())
            continue
        if in_info:
            indent = len(line) - len(line.lstrip())
            if indent <= info_indent:
                break
            if stripped.startswith("version:"):
                return stripped.split(":", 1)[1].strip().strip('"')
    raise AssertionError("info.version not found in schema")


def _read_hash_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip()
    return values


@pytest.mark.parametrize("schema_root", SCHEMA_ROOTS, ids=("v1", "v2"))
def test_schema_hash_is_stable(schema_root: Path) -> None:
    schema_path = schema_root / "schema.yaml"
    hash_path = schema_root / "schema.hash"
    schema_text = schema_path.read_text(encoding="utf-8")
    schema_hash = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
    stored = _read_hash_file(hash_path.read_text(encoding="utf-8"))
    stored_hash = stored.get("sha256")
    stored_version = stored.get("version")

    assert stored_hash, "schema.hash must define sha256"
    assert stored_version, "schema.hash must define version"

    schema_version = _extract_version(schema_text)
    assert schema_version == stored_version, (
        "Schema version must match schema.hash before updating"
    )
    assert schema_hash == stored_hash, (
        f"Schema changed. Update {hash_path.relative_to(REPO_ROOT)} and bump "
        "info.version for breaking changes."
    )
