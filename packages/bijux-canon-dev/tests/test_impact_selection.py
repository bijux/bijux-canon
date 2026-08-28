from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from bijux_canon_dev.verification.impact_selection import select_checks


def _check_ids(*paths: str) -> set[str]:
    return {check.check_id for check in select_checks(paths).checks}


def test_runtime_source_selects_owned_and_restart_contracts() -> None:
    selected = select_checks(
        [
            (
                "packages/bijux-canon-runtime/src/"
                "bijux_canon_runtime/application/runtime_configuration.py"
            )
        ]
    )

    assert {check.check_id for check in selected.checks} == {
        "runtime-local-vertical",
        "runtime-tests",
    }
    assert "restart and replay" in selected.consumers
    assert "artifacts/**" in selected.generated_outputs
    assert all(check.reasons for check in selected.checks)


def test_schema_change_escalates_to_runtime_api_and_owned_tests() -> None:
    assert _check_ids(
        "packages/bijux-canon-runtime/src/bijux_canon_runtime/api/v2/schemas.py"
    ) == {
        "runtime-api",
        "runtime-local-vertical",
        "runtime-tests",
    }


def test_documentation_change_selects_docs_without_product_suites() -> None:
    assert _check_ids("docs/getting-started.md") == {"docs"}


def test_release_metadata_selects_lock_and_install_contracts() -> None:
    assert _check_ids("packages/bijux-canon-runtime/pyproject.toml") == {
        "dependency-lock",
        "release-install-vertical",
        "runtime-tests",
    }


def test_truth_change_selects_content_and_document_contracts() -> None:
    assert _check_ids("examples/ancient-dna-research/truth/qrels.jsonl") == {
        "docs",
        "research-content-vertical",
    }


def test_override_can_only_add_known_checks() -> None:
    selected = select_checks(
        ["docs/index.md"],
        added_checks=["runtime-local-vertical"],
    )
    assert {check.check_id for check in selected.checks} == {
        "docs",
        "runtime-local-vertical",
    }
    override = next(
        check for check in selected.checks if check.check_id == "runtime-local-vertical"
    )
    assert override.rule_ids == ("maintainer-override",)

    with pytest.raises(ValueError, match="unknown additive check"):
        select_checks(["docs/index.md"], added_checks=["not-a-check"])


def test_unmapped_owned_path_uses_safe_fallback() -> None:
    selected = select_checks(["LICENSE"])

    assert {check.check_id for check in selected.checks} == {"repository-configuration"}
    assert selected.matched_rule_ids == ("unmapped-path-fallback",)


def test_cli_emits_stable_json_for_explicit_paths() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bijux_canon_dev.verification.impact_selection",
            "--path",
            "packages/bijux-canon-runtime/src/bijux_canon_runtime/api/v2/schemas.py",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == ("bijux.canon.verification-impact-selection.v1")
    assert [check["check_id"] for check in payload["checks"]] == [
        "runtime-api",
        "runtime-local-vertical",
        "runtime-tests",
    ]
    assert all(check["reasons"] for check in payload["checks"])


def test_cli_reads_worktree_changes_when_paths_are_omitted(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("guide\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bijux_canon_dev.verification.impact_selection",
            "--repo",
            str(tmp_path),
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["paths"] == ["docs/guide.md"]
    assert [check["check_id"] for check in payload["checks"]] == ["docs"]
