# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: MIT
from __future__ import annotations
from pathlib import Path

import pytest


def test_core_has_no_todo_fixme():
    root = Path(__file__).parents[2] / "src" / "bijux_vex" / "core"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text()
        if "TODO" in text or "FIXME" in text:
            offenders.append(str(path))
    assert not offenders, f"TODO/FIXME found in core: {', '.join(offenders)}"


def test_freeze_docs_exist():
    root = Path(__file__).parents[2]
    for doc in [
        root / "docs/spec/mental_model.md",
        root / "docs/spec/failure_semantics.md",
        root / "docs/spec/vdb_profile.md",
        root / "docs/maintainer/freeze_criteria.md",
    ]:
        assert doc.exists(), f"Missing required freeze doc: {doc}"


def test_structure_parity_submodules():
    src_root = Path(__file__).parents[2] / "src" / "bijux_vex"
    tests_root = Path(__file__).parents[1] / "unit"
    src_dirs = {
        rel.parts[0]
        for rel in (p.relative_to(src_root) for p in src_root.rglob("*.py"))
        if rel.parts
    }
    test_dirs = {p.name for p in tests_root.iterdir() if p.is_dir()}
    missing = sorted((src_dirs & {"core", "domain"}) - test_dirs)
    assert not missing, f"Missing test directory mirrors: {', '.join(missing)}"
