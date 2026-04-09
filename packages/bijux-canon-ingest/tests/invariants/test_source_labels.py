# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import re

_BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bBijux RAG\b", "legacy package label"),
    (r"end-of-Bijux RAG", "migration-era package label"),
    (r"\bModules? [0-9]+\b", "numbered module label"),
    (r"\bCore [0-9]+\b", "numbered core label"),
    (r"\bM0[0-9]+\b", "numbered milestone label"),
)


def test_source_files_use_durable_labels() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src" / "bijux_canon_ingest"

    offenders: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern, reason in _BANNED_PATTERNS:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(
                    f"{path.relative_to(package_root)}:{line}: {reason}: {match.group(0)!r}"
                )

    assert offenders == []
