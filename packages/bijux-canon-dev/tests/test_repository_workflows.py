from __future__ import annotations

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


def _workflow_docs() -> list[Path]:
    package_root = REPO_ROOT / "packages"
    return [
        REPO_ROOT / "README.md",
        *sorted(package_root.glob("*/README.md")),
        *sorted(package_root.glob("*/docs/maintainer/pypi.md")),
    ]


def _uses_setup_uv_with_lock_cache(step: Any) -> bool:
    if not isinstance(step, dict):
        return False
    uses = step.get("uses")
    if not isinstance(uses, str) or not uses.startswith("astral-sh/setup-uv@v8"):
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
    repository = jobs.get("repository", {})
    package = jobs.get("package", {})

    assert repository.get("name") == "repository-contracts"
    repository_steps = repository.get("steps", [])
    assert any(_uses_setup_uv_with_lock_cache(step) for step in repository_steps)
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
    compat_entries = [
        entry
        for entry in build_include
        if str(entry.get("package_dir", "")).startswith("packages/compat-")
    ]
    assert compat_entries
    assert all(
        entry.get("makefile_path") == "makes/packages/compat-package.mk"
        for entry in compat_entries
    )


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
        assert any(_uses_setup_uv_with_lock_cache(step) for step in steps), (
            "reusable workflow job is missing setup-uv"
        )

    inputs = _workflow_call_inputs(ci_workflow)
    assert "cache_dependency_path" not in inputs
    build_inputs = _workflow_call_inputs(build_workflow)
    assert "cache_dependency_path" not in build_inputs
    assert "upload_paths" not in build_inputs
    assert "makefile_path" in build_inputs
    build_steps = build_workflow["jobs"]["build"].get("steps", [])
    stage_step = next(
        step for step in build_steps if step.get("name") == "Stage publish artifacts"
    )
    stage_script = stage_step["run"]
    assert 'find "$dist_dir" -type f' in stage_script
    assert "No publish artifacts found under $dist_dir" in stage_script
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
    assert {"verify.yml", "publish.yml", "deploy-docs.yml"} <= root_workflows
    assert not failures, "workflow doc links failed:\n" + "\n".join(failures)
