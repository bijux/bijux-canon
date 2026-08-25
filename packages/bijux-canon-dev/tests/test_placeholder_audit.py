from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_canon_dev.release.placeholder_audit import (
    PlaceholderAuditError,
    audit_repository,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "configs" / "placeholder-audit.json"


def test_repository_markers_have_exact_reviewed_classifications() -> None:
    report = audit_repository(REPO_ROOT, POLICY)

    assert report["result"] == "passed"
    assert report["occurrence_count"] == 52
    assert report["classifications"] == {
        "explicit_experimental_or_deprecated_limitation": 22,
        "implemented_product_path": 13,
        "valid_abstract_method_or_template": 17,
    }


def test_public_marker_rules_name_existing_acceptance_tests() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    public_rules = [rule for rule in policy["rules"] if rule["public_surface"]]

    assert public_rules
    assert all(rule["acceptance_tests"] for rule in public_rules)
    assert all(
        (REPO_ROOT / test_path).is_file()
        for rule in public_rules
        for test_path in rule["acceptance_tests"]
    )


def test_unreviewed_marker_fails_closed(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "README.md").write_text("TODO: fabricate success\n", encoding="utf-8")
    (repository / "policy.json").write_text(
        json.dumps(
            {
                "excluded_exact_paths": [],
                "excluded_prefixes": [],
                "rules": [],
                "schema_version": "bijux.canon.placeholder_audit_policy.v1",
            }
        ),
        encoding="utf-8",
    )
    import subprocess

    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "add", "README.md"), cwd=repository, check=True)

    with pytest.raises(PlaceholderAuditError, match="exactly one policy rule"):
        audit_repository(repository, repository / "policy.json")
