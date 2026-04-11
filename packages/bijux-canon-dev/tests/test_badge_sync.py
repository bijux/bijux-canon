from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.docs.badge_sync import load_badge_catalog
from bijux_canon_dev.docs.badge_sync import synchronize_badges


def test_badge_catalog_exposes_expected_templates() -> None:
    catalog = load_badge_catalog()
    assert set(catalog) == {
        "family-docs-badge",
        "family-ghcr-badge",
        "family-pypi-badge",
        "package-summary",
        "repository-summary",
    }


def test_badge_surfaces_are_synchronized() -> None:
    assert synchronize_badges(check=True) == []
