from __future__ import annotations

import json
from pathlib import Path
import tomllib
from typing import Any, cast

REPOSITORY = Path(__file__).resolve().parents[3]
RELEASE_VERSION = "0.4.0"
RELEASE_DOCUMENT = (
    REPOSITORY / "docs" / "01-bijux-canon" / "operations" / "release-0.4.0.md"
)


def _workspace() -> dict[str, Any]:
    with (REPOSITORY / "pyproject.toml").open("rb") as handle:
        document = tomllib.load(handle)
    return cast(dict[str, Any], document["tool"]["bijux_canon"])


def _distribution(package_key: str, package_dirs: dict[str, str]) -> str:
    with (REPOSITORY / package_dirs[package_key] / "pyproject.toml").open(
        "rb"
    ) as handle:
        document = tomllib.load(handle)
    return cast(str, document["project"]["name"])


def test_release_document_covers_exact_distribution_and_changelog_family() -> None:
    workspace = _workspace()
    package_dirs = cast(dict[str, str], workspace["package_dirs"])
    package_keys = cast(list[str], workspace["packages"])
    distributions = {
        _distribution(package_key, package_dirs) for package_key in package_keys
    }
    release_text = RELEASE_DOCUMENT.read_text(encoding="utf-8")

    assert len(distributions) == 12
    distribution_rows = [
        line
        for line in release_text.splitlines()
        if line.startswith(("| `bijux-", "| `agentic-flows`"))
    ]
    assert len(distribution_rows) == 12
    for package_key in package_keys:
        distribution = _distribution(package_key, package_dirs)
        assert f"| `{distribution}` |" in release_text
        assert package_dirs[package_key] in release_text
        changelog = (REPOSITORY / package_dirs[package_key] / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )
        assert f"## [{RELEASE_VERSION}] - Unreleased" in changelog
        if package_key.startswith("compat-"):
            candidate_entry = changelog.split("## 0.3.9", maxsplit=1)[0]
            assert "### Deprecated" in candidate_entry

    runtime_changelog = (
        REPOSITORY / package_dirs["bijux-canon-runtime"] / "CHANGELOG.md"
    ).read_text(encoding="utf-8")
    assert "### Deprecated" in runtime_changelog.split("## [0.3.9]", maxsplit=1)[0]


def test_release_document_matches_publication_tiers_and_internal_boundary() -> None:
    workspace = _workspace()
    package_dirs = cast(dict[str, str], workspace["package_dirs"])
    release_text = RELEASE_DOCUMENT.read_text(encoding="utf-8")
    public_keys = cast(list[str], workspace["public_release_packages"])
    public_distributions = {
        _distribution(package_key, package_dirs) for package_key in public_keys
    }

    assert len(public_distributions) == 11
    assert "Do not publish `bijux-canon-dev`." in release_text
    tiers = cast(list[list[str]], workspace["release_publication_tiers"])
    for tier_index, package_keys in enumerate(tiers, start=1):
        marker = f"{tier_index}. "
        start = release_text.index(marker, release_text.index("## Publication Order"))
        next_marker = f"{tier_index + 1}. "
        end = (
            release_text.index(next_marker, start)
            if tier_index < len(tiers)
            else release_text.index("\n\nDo not publish", start)
        )
        tier_text = release_text[start:end]
        for package_key in package_keys:
            distribution = _distribution(package_key, package_dirs)
            assert f"`{distribution}`" in tier_text


def test_release_document_covers_governed_deprecations_and_runbook_sections() -> None:
    policy = json.loads(
        (REPOSITORY / "configs" / "semver-compatibility.json").read_text(
            encoding="utf-8"
        )
    )
    release_text = RELEASE_DOCUMENT.read_text(encoding="utf-8")

    for deprecation in policy["deprecations"]:
        surface = cast(str, deprecation["surface"])
        if surface.startswith("distribution/import/command:"):
            assert f"`{surface.rsplit(':', maxsplit=1)[-1]}`" in release_text
        else:
            assert "Runtime v1 run and replay" in release_text
        assert cast(str, deprecation["removal_not_before"]) in release_text

    for heading in (
        "## Distribution Notes and Install Profiles",
        "## Breaking and Deprecated Behavior",
        "## Upgrade Procedure",
        "## Candidate Verification Record",
        "## Known Limitations",
        "## Publication Order and Approval Gate",
        "## Rollback Triggers and Procedure",
        "## Post-Release Checks",
    ):
        assert heading in release_text


def test_release_commands_and_navigation_match_installed_surfaces() -> None:
    release_text = RELEASE_DOCUMENT.read_text(encoding="utf-8")
    pyproject = tomllib.loads(
        (REPOSITORY / "packages" / "bijux-canon-dev" / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    scripts = cast(dict[str, str], pyproject["project"]["scripts"])
    required_commands = {
        "bijux-canon-wheel-inventory",
        "bijux-canon-installation-matrix",
        "bijux-canon-extras-matrix",
        "bijux-canon-python-support",
        "bijux-canon-family-compatibility",
        "bijux-canon-supply-chain",
        "bijux-canon-release-candidate",
    }

    assert required_commands.issubset(scripts)
    assert all(command in release_text for command in required_commands)
    assert "make candidate-frozen" in release_text
    assert "make frozen-status GATE=candidate" in release_text
    assert "make frozen-summary GATE=candidate" in release_text
    assert release_text.count("uv run --frozen --python 3.11") >= 2
    assert "Version 0.4.0 Release Candidate" in (REPOSITORY / "mkdocs.yml").read_text(
        encoding="utf-8"
    )
