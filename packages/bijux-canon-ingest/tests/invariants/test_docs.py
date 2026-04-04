# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path
import re


_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _markdown_links(path: Path) -> list[str]:
    return [
        match.group(1)
        for match in _MARKDOWN_LINK_RE.finditer(path.read_text(encoding="utf-8"))
    ]


def test_local_markdown_links_resolve() -> None:
    package_root = Path(__file__).resolve().parents[2]
    markdown_files = [
        *package_root.glob("README.md"),
        *sorted((package_root / "docs").glob("*.md")),
    ]

    missing: list[str] = []
    for markdown_file in markdown_files:
        for raw_link in _markdown_links(markdown_file):
            if "://" in raw_link or raw_link.startswith("#"):
                continue
            link = raw_link.split("#", 1)[0]
            if not link:
                continue
            target = (markdown_file.parent / link).resolve()
            if not target.exists():
                missing.append(
                    f"{markdown_file.relative_to(package_root)} -> {raw_link}"
                )

    assert missing == []


def test_docs_index_lists_every_package_doc() -> None:
    package_root = Path(__file__).resolve().parents[2]
    docs_root = package_root / "docs"
    index_path = docs_root / "index.md"
    index_text = index_path.read_text(encoding="utf-8")
    documented = {
        path.name for path in docs_root.glob("*.md") if path.name != "index.md"
    }

    missing = sorted(name for name in documented if f"({name})" not in index_text)
    assert missing == []
