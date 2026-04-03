# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path


def test_doc_to_code_map_modules_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    p = root / "docs" / "spec" / "doc_to_code_map.md"
    assert p.exists(), "doc_to_code_map.md missing"
    data = p.read_text(encoding="utf-8").splitlines()
    for line in data:
        if "src/" not in line:
            continue
        parts = line.split("`")
        modules = [seg for seg in parts if seg.startswith("src/")]
        for mod in modules:
            assert (root / mod).exists(), f"Mapped module missing: {mod}"


def test_status_and_breaking_markers() -> None:
    root = Path(__file__).resolve().parents[2]
    for md in root.glob("docs/**/*.md"):
        text = md.read_text(encoding="utf-8")
        assert "STATUS:" in text, f"{md} missing STATUS header"
        if "BREAKING_IF_CHANGED" in text:
            assert "BREAKING_IF_CHANGED: true" in text, f"{md} malformed BREAKING marker"
