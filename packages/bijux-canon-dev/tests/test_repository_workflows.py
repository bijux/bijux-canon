from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
EXPECTED_WORKFLOWS = {
    "build-release-artifacts.yml",
    "ci-package.yml",
    "deploy-docs.yml",
    "publish.yml",
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
EXPECTED_PUBLISH_PACKAGES = {
    "bijux-canon-runtime",
    "bijux-canon-agent",
    "bijux-canon-ingest",
    "bijux-canon-reason",
    "bijux-canon-index",
    "agentic-flows",
    "bijux-agent",
    "bijux-rag",
    "bijux-rar",
    "bijux-vex",
}


def _workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    assert isinstance(data, dict)
    return data


def _matrix_include(job: dict[str, Any]) -> list[dict[str, Any]]:
    strategy = job.get("strategy", {})
    matrix = strategy.get("matrix", {})
    include = matrix.get("include", [])
    return include if isinstance(include, list) else []


def _workflow_call_inputs(workflow: dict[str, Any]) -> dict[str, Any]:
    on_block = workflow.get("on", workflow.get(True, {}))
    if not isinstance(on_block, dict):
        return {}
    workflow_call = on_block.get("workflow_call", {})
    return workflow_call.get("inputs", {}) if isinstance(workflow_call, dict) else {}


def test_workflow_tree_is_standardized() -> None:
    found = {path.name for path in WORKFLOWS_DIR.glob("*.yml")}
    assert found == EXPECTED_WORKFLOWS


def test_verify_workflow_uses_repo_contract_job_and_package_matrix() -> None:
    workflow = _workflow(WORKFLOWS_DIR / "verify.yml")
    jobs = workflow.get("jobs", {})
    repository = jobs.get("repository", {})
    package = jobs.get("package", {})

    assert repository.get("name") == "repository-contracts"
    repository_steps = repository.get("steps", [])
    assert any(
        isinstance(step, dict)
        and step.get("uses") == "astral-sh/setup-uv@v8"
        and step.get("with", {}).get("cache-dependency-glob") == "uv.lock"
        for step in repository_steps
    )
    assert any(
        isinstance(step, dict)
        and step.get("name") == "Verify repository automation contracts"
        and "check-shared-bijux-py" in step.get("run", "")
        and "check-config-layout" in step.get("run", "")
        and "check-make-layout" in step.get("run", "")
        for step in repository_steps
    )
    assert package.get("needs") == "repository"
    assert package.get("uses") == "./.github/workflows/ci-package.yml"

    include = _matrix_include(package)
    found = {entry["package_slug"] for entry in include}
    assert found == EXPECTED_VERIFY_PACKAGES

    runtime = next(
        entry for entry in include if entry["package_slug"] == "bijux-canon-runtime"
    )
    assert runtime["check_targets"] == (
        '["quality", "security", "docs", "build", "sbom", "api", "openapi-drift"]'
    )
    assert runtime["api_toolchain_targets"] == '["api", "openapi-drift"]'

    ingest = next(
        entry for entry in include if entry["package_slug"] == "bijux-canon-ingest"
    )
    assert ingest["test_python_versions"] == '["3.11", "3.12", "3.13"]'

    dev = next(entry for entry in include if entry["package_slug"] == "bijux-canon-dev")
    assert dev["check_targets"] == '["quality", "security", "build", "sbom"]'


def test_publish_workflow_uses_matrix_release_contract() -> None:
    workflow = _workflow(WORKFLOWS_DIR / "publish.yml")
    jobs = workflow.get("jobs", {})
    build = jobs.get("build", {})
    publish = jobs.get("publish", {})

    assert build.get("uses") == "./.github/workflows/build-release-artifacts.yml"
    assert publish.get("needs") == "build"
    assert publish.get("environment", {}).get("name") == "pypi"
    assert publish.get("permissions") == {"contents": "read"}

    publish_steps = publish.get("steps", [])
    assert any(
        isinstance(step, dict)
        and step.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
        and step.get("with", {}).get("password") == "${{ secrets.PYPI_API_TOKEN }}"
        for step in publish_steps
    )

    build_include = _matrix_include(build)
    publish_include = _matrix_include(publish)
    build_packages = {entry["package_slug"] for entry in build_include}
    publish_packages = {entry["package_slug"] for entry in publish_include}

    assert build_packages == EXPECTED_PUBLISH_PACKAGES
    assert publish_packages == EXPECTED_PUBLISH_PACKAGES
    assert all(entry.get("build_targets") == "build sbom" for entry in build_include)

    index = next(
        entry for entry in build_include if entry["package_slug"] == "bijux-canon-index"
    )
    assert index["dist_subdir"] == "release"


def test_reusable_workflows_use_uv_cache_contract() -> None:
    ci_workflow = _workflow(WORKFLOWS_DIR / "ci-package.yml")
    build_workflow = _workflow(WORKFLOWS_DIR / "build-release-artifacts.yml")
    docs_workflow = _workflow(WORKFLOWS_DIR / "deploy-docs.yml")

    reusable_jobs = [
        ci_workflow["jobs"]["tests"],
        ci_workflow["jobs"]["checks"],
        ci_workflow["jobs"]["lint"],
        build_workflow["jobs"]["build"],
        docs_workflow["jobs"]["build"],
    ]

    for job in reusable_jobs:
        steps = job.get("steps", [])
        assert any(
            isinstance(step, dict)
            and step.get("uses") == "astral-sh/setup-uv@v8"
            and step.get("with", {}).get("cache-dependency-glob") == "uv.lock"
            for step in steps
        ), "reusable workflow job is missing setup-uv"

    inputs = _workflow_call_inputs(ci_workflow)
    assert "cache_dependency_path" not in inputs
    build_inputs = _workflow_call_inputs(build_workflow)
    assert "cache_dependency_path" not in build_inputs
    assert "upload_paths" not in build_inputs
