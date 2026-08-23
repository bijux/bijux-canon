from __future__ import annotations

import subprocess
from configparser import ConfigParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["make", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _pytest_config() -> ConfigParser:
    parser = ConfigParser()
    parser.read(REPO_ROOT / "configs" / "pytest.ini", encoding="utf-8")
    return parser


def _pytest_testpaths() -> set[str]:
    raw_value = _pytest_config()["pytest"]["testpaths"]
    return {line.strip() for line in raw_value.splitlines() if line.strip()}


def test_root_pytest_configuration_covers_all_package_test_directories() -> None:
    testpaths = _pytest_testpaths()
    expected_paths = {
        test_dir.relative_to(REPO_ROOT).as_posix()
        for test_dir in (REPO_ROOT / "packages").glob("*/tests")
    }
    assert testpaths == expected_paths


def test_root_help_exposes_stable_focused_and_vertical_lanes() -> None:
    output = _make_output("help")

    expected_targets = {
        "test-focused-agent",
        "test-focused-index",
        "test-focused-ingest",
        "test-focused-reason",
        "test-focused-runtime",
        "test-vertical-document-formats",
        "test-vertical-release-install",
        "test-vertical-research-content",
        "test-vertical-runtime-local",
    }
    assert all(target in output for target in expected_targets)


def test_focused_lanes_dry_run_the_named_package_only() -> None:
    package_by_target = {
        "test-focused-agent": "bijux-canon-agent",
        "test-focused-index": "bijux-canon-index",
        "test-focused-ingest": "bijux-canon-ingest",
        "test-focused-reason": "bijux-canon-reason",
        "test-focused-runtime": "bijux-canon-runtime",
    }

    for target, package in package_by_target.items():
        output = _make_output("--dry-run", target)
        assert f"PACKAGE={package}" in output
        assert "test-all" not in output


def test_vertical_lanes_dry_run_bounded_named_paths() -> None:
    evidence_by_target = {
        "test-vertical-document-formats": "test_citation_lineage.py",
        "test-vertical-release-install": "test_wheel_inventory.py",
        "test-vertical-research-content": "test_research_questions.py",
        "test-vertical-runtime-local": "test_capability_discovery.py",
    }

    for target, evidence_path in evidence_by_target.items():
        output = _make_output("--dry-run", target)
        assert evidence_path in output
        assert "test-all" not in output
