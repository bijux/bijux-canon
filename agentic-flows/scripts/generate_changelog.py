# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import argparse
from pathlib import Path
import sys


SECTION_TITLES = {
    "added": "Added",
    "changed": "Changed",
    "fixed": "Fixed",
}

DEFAULT_LINES = {
    "added": "* (add new entries via fragments in `changelog.d/`)",
    "changed": "* (add here)",
    "fixed": "* (add here)",
}


def load_fragments(folder: Path) -> dict[str, list[str]]:
    sections = {key: [] for key in SECTION_TITLES}
    if not folder.exists():
        return sections
    for path in sorted(folder.glob("*.md")):
        if path.name.startswith("."):
            continue
        prefix = path.name.split(".", 1)[0]
        if prefix not in sections:
            continue
        text = path.read_text().strip()
        if text:
            sections[prefix].append(text)
    return sections


def render_unreleased(sections: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for key, title in SECTION_TITLES.items():
        lines.append(f"### {title}")
        entries = sections.get(key) or []
        if entries:
            for entry in entries:
                lines.append(f"* {entry}")
        else:
            lines.append(DEFAULT_LINES[key])
        lines.append("")
    return "\n".join(lines).rstrip()


def update_changelog(changelog_path: Path, fragments_dir: Path) -> str:
    content = changelog_path.read_text()
    start_token = "<!-- unreleased start -->"
    end_token = "<!-- unreleased end -->"
    if start_token not in content or end_token not in content:
        raise ValueError("CHANGELOG missing unreleased markers.")
    sections = load_fragments(fragments_dir)
    rendered = render_unreleased(sections)
    before, rest = content.split(start_token, 1)
    _, after = rest.split(end_token, 1)
    return f"{before}{start_token}\n{rendered}\n{end_token}{after}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--changelog", type=Path, default=Path("CHANGELOG.md")
    )
    parser.add_argument(
        "--fragments", type=Path, default=Path("changelog.d")
    )
    args = parser.parse_args()

    if not args.changelog.exists():
        raise FileNotFoundError(f"{args.changelog} not found")
    updated = update_changelog(args.changelog, args.fragments)
    if args.check:
        if updated != args.changelog.read_text():
            print("CHANGELOG.md is out of date. Run scripts/generate_changelog.py.")
            return 1
        return 0
    args.changelog.write_text(updated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
