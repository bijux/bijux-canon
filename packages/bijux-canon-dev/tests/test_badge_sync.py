from __future__ import annotations

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.docs.badge_sync import BadgeTarget
from bijux_canon_dev.docs.badge_sync import load_badge_catalog
from bijux_canon_dev.docs.badge_sync import render_badge_block
from bijux_canon_dev.docs.badge_sync import synchronize_badges

GENERATED_BLOCK_RE = re.compile(
    r"<!-- bijux-canon-badges:generated:start -->.*?<!-- bijux-canon-badges:generated:end -->",
    re.DOTALL,
)


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
    assert rendered.count("https://img.shields.io/pypi/v/") == 10
    assert rendered.count("/pkgs/container/") == 10
    assert rendered.count("https://bijux.io/bijux-canon/") == 5
    assert "https://img.shields.io/badge/runtime-ghcr" in rendered
    assert "https://img.shields.io/badge/agent-ghcr" in rendered
    assert rendered.index("https://img.shields.io/pypi/v/") < rendered.index(
        "https://img.shields.io/badge/runtime-ghcr"
    )
    assert rendered.index("https://img.shields.io/badge/runtime-ghcr") < rendered.index(
        "https://img.shields.io/badge/docs-runtime"
    )


def test_package_badge_block_prioritizes_the_current_distribution() -> None:
    rendered = render_badge_block(
        BadgeTarget(
            path=Path("packages/compat-agentic-flows/README.md"),
            kind="package",
            package_slug="compat-agentic-flows",
        )
    )
    assert "\n[![agentic-flows](https://img.shields.io/pypi/v/agentic-flows" in rendered
    assert "\n[![agentic-flows](https://img.shields.io/badge/agentic--flows-ghcr" in rendered
    assert "\n[![bijux-canon-runtime docs](https://img.shields.io/badge/docs-runtime" in rendered
    assert "agentic-flows docs" not in rendered
    assert rendered.index("https://img.shields.io/pypi/v/agentic-flows") < rendered.index(
        "https://img.shields.io/badge/agentic--flows-ghcr"
    )
    assert rendered.index("https://img.shields.io/badge/agentic--flows-ghcr") < rendered.index(
        "https://img.shields.io/badge/docs-runtime"
    )


def test_badge_surfaces_are_synchronized() -> None:
    assert synchronize_badges(check=True) == []


def test_readme_surfaces_only_use_generated_badges() -> None:
    targets = [
        Path("README.md"),
        Path("docs/index.md"),
        Path("packages/bijux-canon-runtime/README.md"),
        Path("packages/bijux-canon-agent/README.md"),
        Path("packages/bijux-canon-ingest/README.md"),
        Path("packages/bijux-canon-reason/README.md"),
        Path("packages/bijux-canon-index/README.md"),
        Path("packages/compat-agentic-flows/README.md"),
        Path("packages/compat-bijux-agent/README.md"),
        Path("packages/compat-bijux-rag/README.md"),
        Path("packages/compat-bijux-rar/README.md"),
        Path("packages/compat-bijux-vex/README.md"),
    ]
    for path in targets:
        text = path.read_text(encoding="utf-8")
        stripped = GENERATED_BLOCK_RE.sub("", text)
        assert "[![" not in stripped, f"{path} contains inline badges outside the generated block"
