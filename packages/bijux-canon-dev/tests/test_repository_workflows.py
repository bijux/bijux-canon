from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_URL_RE = re.compile(
    r"https://github\.com/(?P<repo>[^/\s]+/[^/\s]+)/actions/workflows/"
    r"(?P<workflow>[A-Za-z0-9_.-]+)"
)
EXPECTED_WORKFLOWS = {
    "automerge-pr.yml",
    "bijux-std.yml",
    "ci.yml",
    "deploy-docs.yml",
    "github-policy.yml",
    "pr-approval-policy.yml",
    "release-artifacts.yml",
    "release-ghcr.yml",
    "release-github.yml",
    "release-pypi.yml",
    "verify.yml",
}
EXPECTED_VERIFY_PACKAGES = {
    "bijux-canon-runtime",
    "bijux-canon-agent",
    "bijux-canon-ingest",
    "bijux-canon-reason",
    "bijux-canon-index",
    "bijux-canon-dev",
}
EXPECTED_PUBLIC_DISTRIBUTIONS = {
    "agentic-flows",
    "bijux-agent",
    "bijux-canon",
    "bijux-canon-agent",
    "bijux-canon-index",
    "bijux-canon-ingest",
    "bijux-canon-reason",
    "bijux-canon-runtime",
    "bijux-rag",
    "bijux-rar",
    "bijux-vex",
}


def _workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    workflow: dict[str, Any] = {}
    for key, value in data.items():
        normalized_key = "on" if key is True else key
        if isinstance(normalized_key, str):
            workflow[normalized_key] = value
    return workflow


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _matrix_include(job: dict[str, Any]) -> list[dict[str, Any]]:
    strategy = _as_dict(job.get("strategy"))
    matrix = _as_dict(strategy.get("matrix"))
    include = matrix.get("include", [])
    return include if isinstance(include, list) else []


def _workflow_call_inputs(workflow: dict[str, Any]) -> dict[str, Any]:
    on_block = _as_dict(workflow.get("on"))
    workflow_call = on_block.get("workflow_call", {})
    return workflow_call.get("inputs", {}) if isinstance(workflow_call, dict) else {}


def _workflow_docs() -> list[Path]:
    package_root = REPO_ROOT / "packages"
    return [
        REPO_ROOT / "README.md",
        *sorted(package_root.glob("*/README.md")),
    ]


def _uses_setup_uv_with_lock_cache(step: Any) -> bool:
    if not isinstance(step, dict):
        return False
    uses = step.get("uses")
    if not isinstance(uses, str) or not uses.startswith("astral-sh/setup-uv@"):
        return False
    with_block = step.get("with", {})
    return (
        isinstance(with_block, dict)
        and with_block.get("cache-dependency-glob") == "uv.lock"
    )


def test_workflow_tree_is_standardized() -> None:
    found = {path.name for path in WORKFLOWS_DIR.glob("*.yml")}
    assert found == EXPECTED_WORKFLOWS


def test_verify_workflow_uses_repo_contract_job_and_package_matrix() -> None:
    workflow = _workflow(WORKFLOWS_DIR / "verify.yml")
    jobs = workflow.get("jobs", {})
    repository_job = _as_dict(jobs.get("repository"))
    package_job = _as_dict(jobs.get("package"))

    checks_steps = repository_job.get("steps", [])
    verify_step = next(
        (
            step
            for step in checks_steps
            if isinstance(step, dict)
            and str(step.get("name")) == "Verify repository automation contracts"
        ),
        {},
    )
    checks_command = str(_as_dict(verify_step).get("run", ""))
    assert "check-shared-bijux-py" in checks_command
    assert "check-config-layout" in checks_command
    assert "check-make-layout" in checks_command

    assert package_job.get("uses") == "./.github/workflows/ci.yml"
    include = _matrix_include(package_job)
    found = {entry["package_slug"] for entry in include if isinstance(entry, dict)}
    assert found == EXPECTED_VERIFY_PACKAGES

    runtime = next(
        entry for entry in include if entry["package_slug"] == "bijux-canon-runtime"
    )
    assert runtime["check_targets"] == (
        '["quality", "security", "docs", "build", "sbom", "api", "openapi-drift"]'
    )
    assert runtime["api_toolchain_targets"] == '["api", "openapi-drift"]'

    dev = next(entry for entry in include if entry["package_slug"] == "bijux-canon-dev")
    assert dev["check_targets"] == '["quality", "security", "build", "sbom"]'

    supported_python = _as_dict(jobs.get("supported_python"))
    supported_matrix = _as_dict(
        _as_dict(supported_python.get("strategy")).get("matrix")
    )
    assert [str(version) for version in supported_matrix["python-version"]] == [
        "3.11",
        "3.12",
        "3.13",
        "3.14",
    ]
    supported_command = next(
        step["run"]
        for step in supported_python["steps"]
        if step.get("name") == "Test every canonical and compatibility distribution"
    )
    for package in (
        "compat-bijux-canon",
        "compat-agentic-flows",
        "compat-bijux-agent",
        "compat-bijux-rag",
        "compat-bijux-rar",
        "compat-bijux-vex",
    ):
        assert package in supported_command

    installed_family = _as_dict(jobs.get("installed_family"))
    installed_command = next(
        step["run"]
        for step in installed_family["steps"]
        if step.get("name") == "Build and install the distribution family"
    )
    assert '" = 13' in installed_command
    assert '"bijux-canon-repository"' in installed_command
    assert '"bijux_canon_repository"' not in installed_command
    assert "uv pip check" in installed_command

    verification_ready = _as_dict(jobs.get("verification_ready"))
    assert verification_ready["needs"] == [
        "policy_gate",
        "repository",
        "package",
        "supported_python",
        "installed_family",
    ]


def test_release_matrices_and_branch_protection_require_product_readiness() -> None:
    release_env = (REPO_ROOT / ".github/release.env").read_text(encoding="utf-8")
    entries = {
        line.split("=", maxsplit=1)[0]: line.split("=", maxsplit=1)[1]
        for line in release_env.splitlines()
        if "=" in line and not line.startswith("#")
    }
    for key in (
        "BIJUX_RELEASE_BUILD_MATRIX_JSON",
        "BIJUX_PYPI_PACKAGE_MATRIX_JSON",
        "BIJUX_GHCR_RELEASE_PACKAGE_MATRIX_JSON",
    ):
        matrix = json.loads(entries[key].strip("'"))
        assert {entry["package_slug"] for entry in matrix} == (
            EXPECTED_PUBLIC_DISTRIBUTIONS
        )

    ruleset = json.loads(
        (REPO_ROOT / ".github/rulesets/main-branch-protection.json").read_text(
            encoding="utf-8"
        )
    )
    required_rule = next(
        rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks"
    )
    contexts = {
        check["context"]
        for check in required_rule["parameters"]["required_status_checks"]
    }
    assert "verification-ready" in contexts


def test_release_workflows_replace_legacy_publish_workflow() -> None:
    release_artifacts = _workflow(WORKFLOWS_DIR / "release-artifacts.yml")
    release_github = _workflow(WORKFLOWS_DIR / "release-github.yml")
    release_pypi = _workflow(WORKFLOWS_DIR / "release-pypi.yml")
    release_ghcr = _workflow(WORKFLOWS_DIR / "release-ghcr.yml")

    for workflow in (release_artifacts, release_github, release_pypi, release_ghcr):
        on_block = _as_dict(workflow.get("on"))
        push_block = _as_dict(on_block.get("push"))
        if push_block:
            tags = push_block.get("tags", [])
            assert isinstance(tags, list)
            assert "v*" in tags
            assert "workflow_dispatch" in on_block
        assert "workflow_call" in on_block

    assert release_artifacts.get("name") == "release-artifacts"
    assert release_artifacts["jobs"]["build"]["name"] == (
        "release-artifacts-${{ inputs.package_slug }}"
    )

    assert release_github.get("name") == "release-github"
    assert release_github["jobs"]["release"]["name"] == "github-release"

    assert release_pypi.get("name") == "release-pypi"
    assert release_pypi["jobs"]["resolve"]["name"] == "resolve-release-pypi-config"
    assert release_pypi["jobs"]["publish_artifact"]["name"].startswith("publish-pypi-")
    assert release_pypi["jobs"]["publish_artifact"]["environment"]["name"] == (
        "${{ matrix.environment_name || needs.resolve.outputs.environment_name }}"
    )

    assert release_ghcr.get("name") == "release-ghcr"
    assert release_ghcr["jobs"]["resolve"]["name"] == "resolve-release-ghcr-config"
    assert release_ghcr["jobs"]["publish"]["name"].startswith("publish-ghcr-")
    assert release_ghcr["jobs"]["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
    }


def test_v040_release_claim_excludes_an_executable_container_image() -> None:
    badge_catalog = (REPO_ROOT / "docs" / "badges.md").read_text(encoding="utf-8")
    release_docs = (
        REPO_ROOT
        / "docs"
        / "01-bijux-canon"
        / "operations"
        / "release-and-versioning.md"
    ).read_text(encoding="utf-8")
    runtime_docs = (
        REPO_ROOT
        / "docs"
        / "06-bijux-canon-runtime"
        / "operations"
        / "release-and-versioning.md"
    ).read_text(encoding="utf-8")
    ghcr_workflow = (WORKFLOWS_DIR / "release-ghcr.yml").read_text(encoding="utf-8")

    assert "GHCR release bundles" in badge_catalog
    assert "oci%20bundle" in badge_catalog
    assert "-ghcr-181717" not in badge_catalog
    assert "Version 0.4.0 ships Python distributions only" in release_docs
    assert "does not ship an executable" in release_docs
    assert "does not provide an executable container or service image" in runtime_docs
    assert "oras push" in ghcr_workflow
    assert "docker build" not in ghcr_workflow
    assert "docker push" not in ghcr_workflow


def test_reusable_workflows_use_uv_cache_contract() -> None:
    ci_wrapper = _workflow(WORKFLOWS_DIR / "ci.yml")
    verify_workflow = _workflow(WORKFLOWS_DIR / "verify.yml")
    build_workflow = _workflow(WORKFLOWS_DIR / "release-artifacts.yml")
    docs_workflow = _workflow(WORKFLOWS_DIR / "deploy-docs.yml")

    ci_uses = str(ci_wrapper["jobs"]["package"]["uses"])
    assert ci_uses.startswith(
        "bijux/bijux-std/.github/workflows/reusable-ci-python-packages.yml@"
    )

    assert verify_workflow["jobs"]["repository"]["name"] == "repository-contracts"
    assert build_workflow["jobs"]["build"]["name"] == (
        "release-artifacts-${{ inputs.package_slug }}"
    )

    reusable_jobs = [
        verify_workflow["jobs"]["repository"],
        build_workflow["jobs"]["build"],
        docs_workflow["jobs"]["build"],
    ]

    for job in reusable_jobs:
        if "uses" in job:
            continue
        steps = job.get("steps", [])
        assert any(_uses_setup_uv_with_lock_cache(step) for step in steps), (
            "reusable workflow job is missing setup-uv"
        )

    inputs = _workflow_call_inputs(ci_wrapper)
    assert "cache_dependency_path" not in inputs
    build_inputs = _workflow_call_inputs(build_workflow)
    assert "cache_dependency_path" not in build_inputs
    assert "upload_paths" not in build_inputs
    assert "makefile_path" in build_inputs
    build_steps = build_workflow["jobs"]["build"].get("steps", [])
    stage_step = next(
        step for step in build_steps if step.get("name") == "Stage publish artifacts"
    )
    release_step = next(
        step
        for step in build_steps
        if step.get("name") == "Stage GitHub release assets"
    )
    stage_script = stage_step["run"]
    release_script = release_step["run"]
    assert 'find "$dist_dir" -type f' in stage_script
    assert "No publish artifacts found under $dist_dir" in stage_script
    assert (
        'asset_name="${{ inputs.package_slug }}-dist-$(basename "$file_path")"'
        in release_script
    )
    assert 'sbom_dir="${ARTIFACTS_DIR}/sbom"' in release_script
    assert "${{ inputs.package_slug }}-sbom-prod.cdx.json" in release_script
    assert "${{ inputs.package_slug }}-sbom-dev.cdx.json" in release_script
    assert "${{ inputs.package_slug }}-sbom-summary.txt" in release_script
    assert (
        'makefile="${{ inputs.makefile_path }}"'
        in build_workflow["jobs"]["build"]["steps"][3]["run"]
        or 'makefile="${{ inputs.makefile_path }}"'
        in build_workflow["jobs"]["build"]["steps"][4]["run"]
    )


def test_markdown_workflow_links_track_checked_in_workflow_tree() -> None:
    expected_repo = "bijux/bijux-canon"
    expected_workflows = {path.name for path in WORKFLOWS_DIR.glob("*.yml")}
    failures: list[str] = []

    for path in _workflow_docs():
        text = path.read_text(encoding="utf-8")
        for match in WORKFLOW_URL_RE.finditer(text):
            repo_slug = match.group("repo")
            workflow_name = match.group("workflow")
            if repo_slug != expected_repo:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: expected repo slug "
                    f"{expected_repo}, found {repo_slug}"
                )
            if workflow_name not in expected_workflows:
                failures.append(
                    f"{path.relative_to(REPO_ROOT)}: unknown workflow {workflow_name}"
                )

    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    root_workflows = {
        match.group("workflow") for match in WORKFLOW_URL_RE.finditer(root_readme)
    }
    assert {"verify.yml", "release-github.yml", "deploy-docs.yml"} <= root_workflows
    assert not failures, "workflow doc links failed:\n" + "\n".join(failures)
