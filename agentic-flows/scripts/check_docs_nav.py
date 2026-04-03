# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import re
from pathlib import Path

import yaml

DOCS_DIR = Path("docs")
MKDOCS_PATH = Path("mkdocs.yml")

LINK_RE = re.compile(r"\[[^\\]]+\\]\\(([^)]+)\\)")


def _collect_nav_entries(nav) -> set[Path]:
    entries: set[Path] = set()
    if isinstance(nav, list):
        for item in nav:
            entries |= _collect_nav_entries(item)
    elif isinstance(nav, dict):
        for _key, value in nav.items():
            entries |= _collect_nav_entries(value)
    elif isinstance(nav, str) and nav.endswith(".md"):
        entries.add(Path(nav))
    return entries


def _normalize_link(link: str) -> str:
    link = link.strip()
    if link.startswith("#"):
        return ""
    if "://" in link or link.startswith("mailto:"):
        return ""
    return link.split("#", 1)[0]


def _scan_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [match.group(1) for match in LINK_RE.finditer(text)]


def main() -> int:
    config = yaml.safe_load(MKDOCS_PATH.read_text(encoding="utf-8"))
    nav_entries = _collect_nav_entries(config.get("nav", []))
    nav_paths = {DOCS_DIR / entry for entry in nav_entries}

    doc_paths = {
        path
        for path in DOCS_DIR.rglob("*.md")
        if "assets" not in path.parts and "overrides" not in path.parts
    }

    missing_in_nav = sorted(doc_paths - nav_paths)
    if missing_in_nav:
        print("Docs not in MkDocs nav:")
        for path in missing_in_nav:
            print(f"- {path}")
        return 1

    missing_links: list[str] = []
    for doc in doc_paths:
        for link in _scan_links(doc):
            target = _normalize_link(link)
            if not target:
                continue
            target_path = (doc.parent / target).resolve()
            if target_path.is_dir():
                target_path = target_path / "index.md"
            if not target_path.exists():
                missing_links.append(f"{doc}: {link}")
                continue
            if DOCS_DIR not in target_path.parents and target_path != DOCS_DIR:
                missing_links.append(f"{doc}: {link}")

    if missing_links:
        print("Broken internal doc links:")
        for entry in sorted(missing_links):
            print(f"- {entry}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
