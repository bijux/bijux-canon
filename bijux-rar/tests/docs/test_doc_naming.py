# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import re
from pathlib import Path


def test_doc_filenames_follow_convention() -> None:
    """Enforce lowercase/underscore .md naming for all docs (recursively)."""
    root = Path(__file__).resolve().parents[2] / "docs"
    pattern = re.compile(r"^[0-9a-z_]+\.md$")
    bad: list[str] = []
    for path in root.rglob("*.md"):
        if not pattern.fullmatch(path.name):
            bad.append(str(path.relative_to(root.parent)))
    if bad:
        raise AssertionError(f"Docs naming violation (lower_snake only): {bad}")


def test_doc_status_tags_present_and_valid() -> None:
    """All docs must declare STATUS: AUTHORITATIVE or STATUS: EXPLANATORY."""
    root = Path(__file__).resolve().parents[2] / "docs"
    allowed = {"STATUS: AUTHORITATIVE", "STATUS: EXPLANATORY"}
    missing: list[str] = []
    invalid: list[str] = []
    for path in root.rglob("*.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        statuses = [ln.strip() for ln in lines if ln.strip().startswith("STATUS:")]
        if not statuses:
            missing.append(str(path.relative_to(root.parent)))
            continue
        for st in statuses:
            if st not in allowed:
                invalid.append(f"{path.relative_to(root.parent)} -> {st}")
    if missing or invalid:
        raise AssertionError(
            f"Docs status errors; missing={missing} invalid={invalid}"
        )
