from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CI_WORKFLOWS = sorted(WORKFLOWS_DIR.glob("ci-*.yml"))
PUBLISH_WORKFLOWS = sorted(WORKFLOWS_DIR.glob("publish-*.yml"))


def _workflow(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_publish_workflows_use_direct_jobs_with_publish_environment() -> None:
    failures: list[str] = []

    for path in PUBLISH_WORKFLOWS:
        workflow = _workflow(path)
        jobs = workflow.get("jobs", {})
        build_job = jobs.get("build")
        publish_job = jobs.get("publish")

        if path.name == "publish-package.yml":
            failures.append(f"{path.name}: reusable publish workflow should not exist")
            continue

        if not isinstance(build_job, dict):
            failures.append(f"{path.name}: missing build job")

        if not isinstance(publish_job, dict):
            failures.append(f"{path.name}: missing publish job")
            continue

        build_uses = build_job.get("uses") if isinstance(build_job, dict) else None
        if build_uses != "./.github/workflows/build-release-artifacts.yml":
            failures.append(
                f"{path.name}: build job should reuse ./.github/workflows/build-release-artifacts.yml"
            )
        if publish_job.get("needs") != "build":
            failures.append(f"{path.name}: publish job should depend on build")
        environment = publish_job.get("environment", {})
        if environment.get("name") != "pypi":
            failures.append(f"{path.name}: publish job should target environment pypi")

    assert not failures, "publish workflows drifted:\n" + "\n".join(failures)


def test_publish_jobs_keep_trusted_publishing_contract() -> None:
    failures: list[str] = []

    for path in PUBLISH_WORKFLOWS:
        workflow = _workflow(path)
        permissions = workflow.get("permissions", {})
        jobs = workflow.get("jobs", {})
        publish_job = jobs.get("publish", {})
        job_permissions = publish_job.get("permissions", {})
        steps = publish_job.get("steps", [])
        publish_step = next(
            (
                step
                for step in steps
                if isinstance(step, dict)
                and step.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
            ),
            None,
        )

        if permissions != {"contents": "read"}:
            failures.append(
                f"{path.name}: workflow permissions should stay contents: read"
            )
        if job_permissions != {"contents": "read"}:
            failures.append(
                f"{path.name}: publish job permissions should stay contents: read"
            )
        if not isinstance(publish_step, dict):
            failures.append(
                f"{path.name}: publish job should still publish via PyPI action"
            )
            continue

        password = publish_step.get("with", {}).get("password")
        if password != "${{ secrets.PYPI_API_TOKEN }}":
            failures.append(
                f"{path.name}: publish job should use secrets.PYPI_API_TOKEN"
            )

    assert not failures, "publish workflow auth contract drifted:\n" + "\n".join(
        failures
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
        assert any(
            isinstance(step, dict) and step.get("uses") == "astral-sh/setup-uv@v8"
            for step in steps
        ), "reusable workflow job is missing setup-uv"
        assert not any(
            isinstance(step, dict) and step.get("name") == "Prepare pip cache directory"
            for step in steps
        ), "reusable workflow job should not prepare a pip cache"

    assert "PIP_CACHE_DIR" not in ci_workflow.get("env", {})
    assert "PIP_DISABLE_PIP_VERSION_CHECK" not in ci_workflow.get("env", {})


def test_wrapper_workflows_cache_against_repository_lockfile() -> None:
    failures: list[str] = []

    for path in [*CI_WORKFLOWS, *PUBLISH_WORKFLOWS]:
        if path.name in {"ci-package.yml", "build-release-artifacts.yml"}:
            continue

        workflow = _workflow(path)
        job = next(iter(workflow.get("jobs", {}).values()), {})
        cache_dependency_path = job.get("with", {}).get("cache_dependency_path")
        if cache_dependency_path != "uv.lock":
            failures.append(f"{path.name}: cache_dependency_path should be uv.lock")

    assert not failures, "workflow cache contract drifted:\n" + "\n".join(failures)
