# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "api" / "v1" / "schema.yaml"
HASH_PATH = REPO_ROOT / "api" / "v1" / "schema.hash"


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


def test_schema_hash_is_stable() -> None:
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_hash = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
    stored = _read_hash_file(HASH_PATH.read_text(encoding="utf-8"))
    stored_hash = stored.get("sha256")
    stored_version = stored.get("version")

    assert stored_hash, "schema.hash must define sha256"
    assert stored_version, "schema.hash must define version"

    schema_version = _extract_version(schema_text)
    assert schema_version == stored_version, (
        "Schema version must match schema.hash before updating"
    )
    assert schema_hash == stored_hash, (
        "Schema changed. Update api/v1/schema.hash and bump info.version "
        "for breaking changes."
    )
