# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import re
from pathlib import Path


def _iter_links(md_path: Path) -> list[tuple[str, str]]:
    text = md_path.read_text(encoding="utf-8")
    links: list[tuple[str, str]] = []
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        label, target = match.group(1), match.group(2)
        links.append((label, target))
    return links


def test_markdown_links_resolve() -> None:
    docs_root = Path(__file__).resolve().parents[2] / "docs"
    errors: list[str] = []
    for md in docs_root.rglob("*.md"):
        for _, target in _iter_links(md):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                continue
            # MkDocs resolves relative to current document
            base = md.parent
            path_part, _, frag = target.partition("#")
            target_path = (base / path_part).resolve()
            if docs_root not in target_path.parents and target_path != docs_root:
                errors.append(f"{md}: link {target} escapes docs/ root")
                continue
            if not target_path.exists():
                errors.append(f"{md}: missing target {target_path.relative_to(docs_root.parent)}")
                continue
            if frag:
                content = target_path.read_text(encoding="utf-8")
                if frag not in content and f'id="{frag}"' not in content and f"#{frag}" not in content:
                    errors.append(f"{md}: fragment #{frag} not found in {target_path.relative_to(docs_root.parent)}")
    if errors:
        raise AssertionError("Broken doc links:\n" + "\n".join(errors))
