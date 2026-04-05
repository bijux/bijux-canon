from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
PUBLISH_PACKAGE_WORKFLOW = WORKFLOWS_DIR / "publish-package.yml"
PUBLISH_WRAPPER_WORKFLOWS = sorted(
    path
    for path in WORKFLOWS_DIR.glob("publish-*.yml")
    if path.name != PUBLISH_PACKAGE_WORKFLOW.name
)


def _workflow(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_publish_wrappers_route_through_shared_publish_workflow() -> None:
    failures: list[str] = []

    for path in PUBLISH_WRAPPER_WORKFLOWS:
        workflow = _workflow(path)
        jobs = workflow.get("jobs", {})
        publish_job = jobs.get("publish")

        if not isinstance(publish_job, dict):
            failures.append(f"{path.name}: missing publish job")
            continue

        uses = publish_job.get("uses")
        if uses != "./.github/workflows/publish-package.yml":
            failures.append(
                f"{path.name}: publish job should reuse ./.github/workflows/publish-package.yml"
            )

    assert not failures, "publish wrapper workflows drifted:\n" + "\n".join(failures)


def test_shared_publish_workflow_keeps_trusted_publishing_contract() -> None:
    workflow = _workflow(PUBLISH_PACKAGE_WORKFLOW)
    permissions = workflow.get("permissions", {})
    jobs = workflow.get("jobs", {})
    publish_job = jobs.get("publish", {})
    job_permissions = publish_job.get("permissions", {})
    steps = publish_job.get("steps", [])

    assert permissions.get("id-token") == "write"
    assert job_permissions.get("id-token") == "write"
    assert any(
        step.get("uses") == "pypa/gh-action-pypi-publish@release/v1"
        for step in steps
        if isinstance(step, dict)
    ), "shared publish workflow should still publish via PyPI trusted publishing"
