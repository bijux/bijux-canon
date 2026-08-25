from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from bijux_canon_dev.release.python_support_matrix import CommandResult
from bijux_canon_dev.release.registry_preflight import run_registry_preflight


def _runner(
    command: Sequence[str], _cwd: Path, _environment: Mapping[str, str]
) -> CommandResult:
    joined = " ".join(command)
    stdout = ""
    if "users/bijux --jq .type" in joined:
        stdout = "User\n"
    elif "api user --jq .login" in joined:
        stdout = "bijux\n"
    elif "repos/bijux/bijux-canon --jq .permissions.push" in joined:
        stdout = "true\n"
    elif "user/packages?package_type=container" in joined:
        stdout = "bijux-canon/example\n"
    return CommandResult(tuple(command), 0, stdout, "", 0.01)


def _unused_pypi(name: str, version: str) -> dict[str, object]:
    return {
        "distribution_name": name,
        "version": version,
        "http_status": 404,
        "status": "unused",
    }


def _mapping(evidence: dict[str, object], field: str) -> dict[str, object]:
    return cast(dict[str, object], evidence[field])


def _records(evidence: dict[str, object], field: str) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], evidence[field])


def test_preflight_proves_all_live_names_unused(tmp_path: Path) -> None:
    evidence = run_registry_preflight(
        repo_root=tmp_path,
        version="0.4.0",
        tag="v0.4.0",
        package_names=("example", "internal-support"),
        container_names=("example",),
        github_repository="bijux/bijux-canon",
        remote="origin",
        git_executable=Path("/usr/bin/git"),
        gh_executable=Path("/usr/bin/gh"),
        runner=_runner,
        pypi_probe=_unused_pypi,
    )

    assert evidence["result"] == "passed"
    assert evidence["retained_failures"] == []
    assert _mapping(evidence, "github_releases")["draft_visibility"] is True
    assert [row["distribution_name"] for row in _records(evidence, "pypi")] == [
        "example",
        "internal-support",
    ]
    assert _records(evidence, "ghcr")[0]["status"] == "unused"


def test_preflight_retains_every_collision(tmp_path: Path) -> None:
    def collision_runner(
        command: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CommandResult:
        baseline = _runner(command, cwd, environment)
        joined = " ".join(command)
        if "ls-remote" in command:
            return CommandResult(tuple(command), 0, "abc\trefs/tags/v0.4.0\n", "", 0.01)
        if "/releases?" in joined:
            return CommandResult(
                tuple(command), 0, "v0.4.0\ttrue\thttps://example.invalid\n", "", 0.01
            )
        if "/versions?" in joined:
            return CommandResult(tuple(command), 0, "42\tv0.4.0\n", "", 0.01)
        return baseline

    def collision_pypi(name: str, version: str) -> dict[str, object]:
        return {
            "distribution_name": name,
            "version": version,
            "http_status": 200,
            "status": "collision",
        }

    evidence = run_registry_preflight(
        repo_root=tmp_path,
        version="0.4.0",
        tag="v0.4.0",
        package_names=("example",),
        container_names=("example",),
        github_repository="bijux/bijux-canon",
        remote="origin",
        git_executable=Path("/usr/bin/git"),
        gh_executable=Path("/usr/bin/gh"),
        runner=collision_runner,
        pypi_probe=collision_pypi,
    )

    assert evidence["result"] == "failed"
    assert _mapping(evidence, "remote_tag")["status"] == "collision"
    assert _mapping(evidence, "github_releases")["status"] == "collision"
    assert _records(evidence, "ghcr")[0]["status"] == "collision"
    assert len(cast(list[str], evidence["retained_failures"])) == 4
