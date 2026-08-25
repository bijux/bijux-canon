from __future__ import annotations

import json
from pathlib import Path

from bijux_canon_dev.release.semver_compatibility import compare_release_surfaces

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "configs" / "semver-compatibility.json"


def test_prior_release_public_surfaces_are_retained() -> None:
    report = compare_release_surfaces(REPO_ROOT, POLICY)

    assert report["result"] == "passed"
    assert report["prior_release"] == "v0.3.9"
    assert len(report["imports"]) == 12
    assert len(report["commands"]) == 12
    assert len(report["schemas"]) == 5
    assert all(not item.get("removed") for family in ("imports", "commands", "schemas") for item in report[family])


def test_deprecations_have_open_windows_and_explicit_alternatives() -> None:
    report = compare_release_surfaces(REPO_ROOT, POLICY)

    assert len(report["deprecations"]) == 7
    assert all(item["alternative"] and item["owner"] for item in report["deprecations"])


def test_workspace_migration_proof_names_rollback_and_acceptance() -> None:
    report = compare_release_surfaces(REPO_ROOT, POLICY)
    workspace = report["workspace_migration"]

    assert len(workspace["acceptance_tests"]) == 2
    assert workspace["rollback_documentation"].endswith("installation-and-setup.md")
    assert all((REPO_ROOT / path).is_file() for path in workspace["acceptance_tests"])


def test_policy_is_canonical_json() -> None:
    payload = json.loads(POLICY.read_text(encoding="utf-8"))
    assert POLICY.read_text(encoding="utf-8") == json.dumps(payload, indent=2, sort_keys=True) + "\n"
