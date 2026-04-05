from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
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

        if permissions.get("id-token") != "write":
            failures.append(f"{path.name}: workflow should request id-token write")
        if job_permissions.get("id-token") != "write":
            failures.append(f"{path.name}: publish job should request id-token write")
        if not any(
            step.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
            for step in steps
            if isinstance(step, dict)
        ):
            failures.append(
                f"{path.name}: publish job should still publish via PyPI trusted publishing"
            )

    assert not failures, (
        "publish workflow trusted-publishing contract drifted:\n"
        + "\n".join(failures)
    )
