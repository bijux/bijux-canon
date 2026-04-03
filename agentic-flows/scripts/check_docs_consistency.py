#!/usr/bin/env python3
"""Ensure MkDocs nav entries map to existing files."""

from __future__ import annotations

from pathlib import Path

import yaml


def _collect_nav_paths(nav) -> list[str]:
    paths: list[str] = []
    if isinstance(nav, list):
        for entry in nav:
            paths.extend(_collect_nav_paths(entry))
    elif isinstance(nav, dict):
        for _, value in nav.items():
            paths.extend(_collect_nav_paths(value))
    elif isinstance(nav, str):
        paths.append(nav)
    return paths


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    mkdocs_path = repo_root / "mkdocs.yml"
    if not mkdocs_path.exists():
        print("mkdocs.yml not found; skipping doc consistency check")
        return 0

    data = yaml.safe_load(mkdocs_path.read_text(encoding="utf-8")) or {}
    docs_dir = repo_root / str(data.get("docs_dir", "docs"))
    nav_paths = _collect_nav_paths(data.get("nav", []))

    missing: list[str] = []
    for rel in nav_paths:
        target = docs_dir / rel
        if not target.exists():
            missing.append(str(target.relative_to(repo_root)))

    if missing:
        print("Missing MkDocs nav files:")
        for entry in missing:
            print(f"  - {entry}")
        return 1

    print("✔ MkDocs nav paths resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
