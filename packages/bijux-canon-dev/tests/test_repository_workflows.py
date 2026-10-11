from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
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
    "dependency-notice.yml",
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
    assert "policy_gate" not in jobs
    repository_job = _as_dict(jobs.get("repository"))
    package_job = _as_dict(jobs.get("package"))
    assert "needs" not in repository_job
    assert package_job["needs"] == "repository"

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
        '["quality", "security", "build", "sbom", "api", "openapi-drift"]'
    )
    assert runtime["api_toolchain_targets"] == '["api", "openapi-drift"]'

    dev = next(entry for entry in include if entry["package_slug"] == "bijux-canon-dev")
    assert dev["check_targets"] == '["quality", "security", "build", "sbom"]'

    supported_python = _as_dict(jobs.get("supported_python"))
    assert supported_python["needs"] == "repository"
    supported_matrix = _as_dict(
        _as_dict(supported_python.get("strategy")).get("matrix")
    )
    assert [str(version) for version in supported_matrix["python-version"]] == [
        "3.11",
        "3.12",
        "3.13",
        "3.14",
    ]
    assert supported_matrix["package_slug"] == [
        "bijux-canon-dev",
        "bijux-canon-runtime",
        "bijux-canon-agent",
        "bijux-canon-ingest",
        "bijux-canon-reason",
        "bijux-canon-index",
        "compat-bijux-canon",
        "compat-agentic-flows",
        "compat-bijux-agent",
        "compat-bijux-rag",
        "compat-bijux-rar",
        "compat-bijux-vex",
    ]
    assert _as_dict(supported_python["strategy"])["max-parallel"] == 12
    assert supported_python["timeout-minutes"] == 30
    supported_command = next(
        step["run"]
        for step in supported_python["steps"]
        if step.get("name") == "Test one supported package distribution"
    )
    assert 'PACKAGE="${{ matrix.package_slug }}" test' in supported_command
    assert "for package in" not in supported_command

    installed_family = _as_dict(jobs.get("installed_family"))
    assert installed_family["needs"] == "repository"
    installed_command = next(
        step["run"]
        for step in installed_family["steps"]
        if step.get("name") == "Build and install the distribution family"
    )
    assert (
        'UV_CACHE_DIR="${RUNNER_TEMP}/bijux-installed-family-uv-cache"'
        in installed_command
    )
    assert '" = 13' in installed_command
    assert '"bijux-canon-repository"' in installed_command
    assert '"bijux_canon_repository"' not in installed_command
    assert "uv pip check" in installed_command

    verification_ready = _as_dict(jobs.get("verification_ready"))
    assert verification_ready["needs"] == [
        "repository",
        "package",
        "supported_python",
        "installed_family",
    ]


def test_dependency_merge_requires_owner_consolidation_without_auto_merge() -> None:
    workflow = _workflow(WORKFLOWS_DIR / "automerge-pr.yml")
    jobs = _as_dict(workflow.get("jobs"))
    workflow_text = (WORKFLOWS_DIR / "automerge-pr.yml").read_text(encoding="utf-8")

    assert set(_as_dict(workflow["on"])) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(jobs) == {"owner-consolidation"}
    assert jobs["owner-consolidation"]["name"] == (
        "dependency / owner consolidation policy"
    )
    assert "gh pr merge" not in workflow_text
    assert "enablePullRequestAutoMerge" not in workflow_text
    assert "pull-requests: write" not in workflow_text


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
        if workflow is release_artifacts:
            assert "workflow_call" in on_block
        else:
            assert set(on_block) == {"workflow_dispatch"}
            dispatch = _as_dict(on_block["workflow_dispatch"])
            inputs = _as_dict(dispatch["inputs"])
            assert inputs["accepted_commit"]["required"] is True
            assert inputs["release_tag"]["required"] is True
            jobs = _as_dict(workflow["jobs"])
            assert jobs["publication_admission"]["name"] == "publication / admission"
            for name, job in jobs.items():
                if name != "publication_admission":
                    assert "publication_admission" in job["needs"]

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

    ci_jobs = _as_dict(ci_wrapper["jobs"])
    assert set(ci_jobs) == {"tests", "checks", "lint"}
    assert all("uses" not in _as_dict(job) for job in ci_jobs.values())

    assert (
        _human_job_name(verify_workflow["jobs"]["repository"]) == "repository-contracts"
    )
    assert build_workflow["jobs"]["build"]["name"] == (
        "release-artifacts-${{ inputs.package_slug }}"
    )

    reusable_jobs = [
        *ci_jobs.values(),
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


DEPENDENCY_PROPOSAL_MATCH = (
    "github.event.pull_request.user.login == 'dependabot[bot]' || "
    "(github.event.pull_request.user.login == 'github-actions[bot]' && "
    "github.event.pull_request.head.ref == 'automation/dependency-lock-refresh')"
)
UNVERIFIED_JOB_PREFIX = (
    "${{ (" + DEPENDENCY_PROPOSAL_MATCH + ") && 'unverified dependency / ' || '' }}"
)


def _human_job_name(job: dict[str, Any]) -> str:
    name = str(job["name"])
    assert name.startswith(UNVERIFIED_JOB_PREFIX)
    return name.removeprefix(UNVERIFIED_JOB_PREFIX)


def _workflow_execution() -> ModuleType:
    package = REPO_ROOT / ".github" / "scripts" / "workflow_execution"
    name = "bijux_canon_workflow_execution"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, package / "__init__.py", submodule_search_locations=[str(package)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _execution_policy() -> dict[str, Any]:
    manifest = json.loads(
        (REPO_ROOT / ".github/standards/repo-config.manifest.json").read_text()
    )
    repository = next(
        entry for entry in manifest["repositories"] if entry["name"] == "bijux-canon"
    )
    policy = _as_dict(repository["workflow_execution_policy"])
    assert policy["dependency_pull_requests"] == "notification-only"
    assert policy["dependency_merge"] == "owner-consolidation"
    assert policy["main_verification"] == "accepted-pull-request"
    return policy


def test_dependency_notice_cannot_replace_required_verification() -> None:
    notice = _workflow(WORKFLOWS_DIR / "dependency-notice.yml")
    assert set(notice["on"]) == {"pull_request_target"}
    assert notice["permissions"] == {"contents": "read"}
    assert set(notice["jobs"]) == {"notice"}
    job = notice["jobs"]["notice"]
    assert job["name"] == "dependency / owner review notice"
    assert job["if"] == ("${{ " + DEPENDENCY_PROPOSAL_MATCH + " }}")
    assert job["timeout-minutes"] == 1
    assert all("uses" not in step for step in job["steps"])
    ruleset = json.loads(
        (REPO_ROOT / ".github/rulesets/main-branch-protection.json").read_text()
    )
    required = {
        check["context"]
        for rule in ruleset["rules"]
        if rule["type"] == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    }
    assert {
        "verification-ready",
        "policy / github",
        "policy / pr approval",
        "std / standard",
        "std / report",
    } <= required
    assert job["name"] not in required
    assert not any(
        context.startswith("unverified dependency / ") for context in required
    )


def test_human_verification_retains_product_and_approval_gates() -> None:
    documents = {
        str(path.relative_to(REPO_ROOT)): _workflow(path)
        for path in WORKFLOWS_DIR.glob("*.yml")
    }
    execution = _workflow_execution()
    execution.validate_owned_execution(documents, _execution_policy())
    for document in documents.values():
        assert "push" not in document["on"]
        if (
            not {
                "pull_request",
                "pull_request_target",
                "pull_request_review",
            }.intersection(document["on"])
            or document is documents[".github/workflows/dependency-notice.yml"]
        ):
            continue
        for job in document["jobs"].values():
            assert (
                "github.event.pull_request.user.login != 'dependabot[bot]'" in job["if"]
            )
            assert "github.actor" not in job["if"]
            human_name = _human_job_name(job)
            assert human_name
            assert "unverified dependency / " + human_name != human_name
    verify = documents[".github/workflows/verify.yml"]
    assert _human_job_name(verify["jobs"]["verification_ready"]) == "verification-ready"
    assert set(verify["jobs"]) == {
        "repository",
        "package",
        "supported_python",
        "installed_family",
        "verification_ready",
    }
    approval = documents[".github/workflows/pr-approval-policy.yml"]
    assert approval["jobs"]
    assert (
        "owner-self-signoff" in (WORKFLOWS_DIR / "pr-approval-policy.yml").read_text()
    )


@pytest.mark.parametrize(
    "mutation", ["guard", "triggering-actor", "required-name", "push", "notice-name"]
)
def test_unverified_or_duplicate_workflow_cannot_pass_execution_admission(
    mutation: str,
) -> None:
    path = WORKFLOWS_DIR / (
        "dependency-notice.yml" if mutation == "notice-name" else "verify.yml"
    )
    document = copy.deepcopy(_workflow(path))
    if mutation == "guard":
        del document["jobs"]["verification_ready"]["if"]
    elif mutation == "triggering-actor":
        job = document["jobs"]["verification_ready"]
        job["if"] = job["if"].replace(
            "github.event.pull_request.user.login", "github.actor"
        )
    elif mutation == "required-name":
        document["jobs"]["verification_ready"]["name"] = "verification-ready"
    elif mutation == "push":
        document["on"]["push"] = {"branches": ["main"]}
    else:
        document["jobs"]["notice"]["name"] = "verification-ready"
    with pytest.raises(ValueError):
        _workflow_execution().validate_owned_execution(
            {str(path.relative_to(REPO_ROOT)): document}, _execution_policy()
        )


def _evaluate_author_admission(
    expression: str, *, event: str, author: str, head: str
) -> bool:
    replacements = {
        "github.event_name": event,
        "github.event.pull_request.user.login": author,
        "github.event.pull_request.head.ref": head,
    }
    for key, value in replacements.items():
        expression = expression.replace(key, repr(value))
    tree = ast.parse(
        expression.replace("&&", " and ").replace("||", " or "), mode="eval"
    )

    def evaluate(node: ast.AST) -> bool | str:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bool)):
            return node.value
        if isinstance(node, ast.BoolOp):
            values = [bool(evaluate(value)) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == len(node.comparators) == 1
        ):
            left, right = evaluate(node.left), evaluate(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        raise AssertionError(
            f"Unsupported author-admission expression: {ast.dump(node)}"
        )

    return bool(evaluate(tree))


@pytest.mark.parametrize(
    ("author", "head", "notification"),
    [
        ("dependabot[bot]", "dependabot/pip/urllib3", True),
        ("github-actions[bot]", "automation/dependency-lock-refresh", True),
        ("github-actions[bot]", "automation/dependency-lock-refresh-extra", False),
        ("github-actions[bot]", "feature/product-interface", False),
        ("bijan", "automation/dependency-lock-refresh", False),
    ],
)
def test_dependency_notice_is_bounded_by_original_author_and_exact_head(
    author: str, head: str, notification: bool
) -> None:
    dependency = _workflow_execution().dependency_prs
    assert dependency.DEPENDENCY_PROPOSAL_MATCH == DEPENDENCY_PROPOSAL_MATCH
    notice = _workflow(WORKFLOWS_DIR / "dependency-notice.yml")
    notice_expression = notice["jobs"]["notice"]["if"][3:-2].strip()
    for event in ("pull_request", "pull_request_target", "pull_request_review"):
        assert (
            _evaluate_author_admission(
                notice_expression, event=event, author=author, head=head
            )
            is notification
        )
        assert (
            _evaluate_author_admission(
                dependency.DEPENDENCY_PR_EXCLUSION,
                event=event,
                author=author,
                head=head,
            )
            is not notification
        )
    assert _evaluate_author_admission(
        dependency.DEPENDENCY_PR_EXCLUSION,
        event="workflow_dispatch",
        author=author,
        head=head,
    )
