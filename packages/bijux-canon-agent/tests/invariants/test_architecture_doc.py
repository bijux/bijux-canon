"""Fail the build when the architecture overview is missing."""

from __future__ import annotations

from pathlib import Path


def test_architecture_doc_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    doc = (
        root.parents[1]
        / "docs"
        / "packages"
        / "bijux-canon-agent"
        / "architecture"
        / "ARCHITECTURE.md"
    )
    assert doc.exists(), (
        "docs/packages/bijux-canon-agent/architecture/ARCHITECTURE.md must document module boundaries"
    )
    assert doc.stat().st_size > 200, (
        "Architecture overview should contain meaningful content"
    )
