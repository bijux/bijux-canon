#!/usr/bin/env python3
"""Validate local markdown links resolve to files in the repo."""

from __future__ import annotations

import re
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _iter_markdown_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.md")
        if "/.venv/" not in str(path)
        and "/.git/" not in str(path)
        and "/artifact/" not in str(path)
        and "/artifacts/" not in str(path)
        and "/site/" not in str(path)
    ]


def _normalize_target(target: str) -> str:
    target = target.strip()
    if not target or target.startswith("#"):
        return ""
    if "://" in target or target.startswith("mailto:"):
        return ""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return target


def _resolve_path(base: Path, target: str, repo_root: Path) -> Path:
    if target.startswith("/"):
        return repo_root / target.lstrip("/")
    return (base / target).resolve()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    missing: list[str] = []

    for md_file in _iter_markdown_files(repo_root):
        base_dir = md_file.parent
        contents = md_file.read_text(encoding="utf-8")
        for match in LINK_RE.findall(contents):
            target = _normalize_target(match)
            if not target:
                continue
            target_path = _resolve_path(base_dir, target, repo_root)
            if not target_path.exists():
                missing.append(f"{md_file.relative_to(repo_root)} -> {match}")

    if missing:
        print("Missing markdown link targets:")
        for entry in missing:
            print(f"  - {entry}")
        return 1

    print("✔ Markdown link targets resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
