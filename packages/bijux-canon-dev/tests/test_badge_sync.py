from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.docs.badge_sync import BadgeTarget
from bijux_canon_dev.docs.badge_sync import load_badge_catalog
from bijux_canon_dev.docs.badge_sync import render_badge_block
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


def test_repository_badge_block_renders_all_public_badge_groups() -> None:
    rendered = render_badge_block(
        BadgeTarget(path=Path("README.md"), kind="repository")
    )
    assert "**PyPI**" in rendered
    assert "**Documentation**" in rendered
    assert "**GHCR**" in rendered
    assert rendered.count("https://img.shields.io/pypi/v/") == 10
    assert rendered.count("/pkgs/container/") == 5
    assert rendered.count("https://bijux.io/bijux-canon/") == 5


def test_package_badge_block_prioritizes_the_current_distribution() -> None:
    rendered = render_badge_block(
        BadgeTarget(
            path=Path("packages/compat-agentic-flows/README.md"),
            kind="package",
            package_slug="compat-agentic-flows",
        )
    )
    assert "**PyPI**\n[![agentic-flows]" in rendered
    assert "**Documentation**\n[![bijux-canon-runtime docs]" in rendered
    assert "**GHCR**\n[![bijux-canon-runtime]" in rendered
    assert "agentic-flows docs" not in rendered
    assert "bijux-canon%2Fagentic-flows" not in rendered


def test_badge_surfaces_are_synchronized() -> None:
    assert synchronize_badges(check=True) == []
