from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _tagged_file(tag: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{tag}:{path}"],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"required tag payload not available: {tag}:{path}")
    return result.stdout


def _section_body(text: str, marker: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip().startswith(marker):
            start = index + 1
            break
    if start is None:
        raise AssertionError(f"missing changelog section {marker!r}")

    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    ignored_prefixes = ("<!--", "[Back to top]")
    return [
        line.rstrip()
        for line in lines[start:end]
        if line.strip() and not line.strip().startswith(ignored_prefixes)
    ]


@pytest.mark.parametrize(
    ("current_path", "current_marker", "tag", "tag_path", "tag_marker"),
    [
        (
            "packages/06-bijux-canon-runtime/CHANGELOG.md",
            "## [0.1.0]",
            "agentic-flows/v0.1.0",
            "CHANGELOG.md",
            "## [0.1.0]",
        ),
        (
            "packages/05-bijux-canon-agent/CHANGELOG.md",
            "## v0.1.0",
            "bijux-agent/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/02-bijux-canon-ingest/CHANGELOG.md",
            "## [0.1.0]",
            "bijux-rag/v0.1.0",
            "CHANGELOG.md",
            "## [0.1.0]",
        ),
        (
            "packages/04-bijux-canon-reason/CHANGELOG.md",
            "## v0.1.0",
            "bijux-rar/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/03-bijux-canon-index/CHANGELOG.md",
            "## 0.1.0",
            "bijux-vex/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/03-bijux-canon-index/CHANGELOG.md",
            "## 0.2.0",
            "bijux-vex/v0.2.0",
            "CHANGELOG.md",
            "## 0.2.0",
        ),
        (
            "packages/compat-agentic-flows/CHANGELOG.md",
            "## 0.1.0",
            "agentic-flows/v0.1.0",
            "CHANGELOG.md",
            "## [0.1.0]",
        ),
        (
            "packages/compat-bijux-agent/CHANGELOG.md",
            "## v0.1.0",
            "bijux-agent/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/compat-bijux-rag/CHANGELOG.md",
            "## [0.1.0]",
            "bijux-rag/v0.1.0",
            "CHANGELOG.md",
            "## [0.1.0]",
        ),
        (
            "packages/compat-bijux-rar/CHANGELOG.md",
            "## v0.1.0",
            "bijux-rar/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/compat-bijux-vex/CHANGELOG.md",
            "## v0.1.0",
            "bijux-vex/v0.1.0",
            "CHANGELOG.md",
            "## v0.1.0",
        ),
        (
            "packages/compat-bijux-vex/CHANGELOG.md",
            "## 0.2.0",
            "bijux-vex/v0.2.0",
            "CHANGELOG.md",
            "## 0.2.0",
        ),
    ],
)
def test_tag_backed_release_history_matches_shipped_changelog(
    current_path: str,
    current_marker: str,
    tag: str,
    tag_path: str,
    tag_marker: str,
) -> None:
    current_text = (REPO_ROOT / current_path).read_text(encoding="utf-8")
    tagged_text = _tagged_file(tag, tag_path)

    assert _section_body(current_text, current_marker) == _section_body(
        tagged_text, tag_marker
    )
