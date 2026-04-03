# SPDX-FileCopyrightText: Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
"""Invariant: OpenAPI schema checksum must stay in sync with committed checksum."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_openapi_schema_checksum_matches_manifest() -> None:
    root = Path(__file__).resolve().parents[2]
    schema_path = root / "api" / "v1" / "schema.yaml"
    checksum_path = root / "docs" / "checksums" / "openapi_v1.sha256"
    checksum_content = checksum_path.read_text(encoding="utf-8")
    relevant_lines = [
        line
        for line in checksum_content.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert relevant_lines, (
        "Checksum manifest is empty; update docs/checksums/openapi_v1.sha256"
    )
    expected = relevant_lines[0].split()[0]
    actual = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    assert actual == expected, (
        "OpenAPI schema checksum changed; update docs/checksums/openapi_v1.sha256"
    )
