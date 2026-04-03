# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from pathlib import Path


def test_doc_to_code_map_targets_exist():
    root = Path(__file__).parents[2]
    doc_map = root / "docs" / "spec" / "doc_to_code_map.md"
    assert doc_map.exists()
    lines = doc_map.read_text().splitlines()
    targets = []
    for line in lines:
        if "→" in line:
            _, rhs = line.split("→", 1)
            targets.extend([seg.strip() for seg in rhs.split(",")])
    missing = [t for t in targets if not (root / t).exists()]
    assert not missing, f"Doc map references missing code: {', '.join(missing)}"
