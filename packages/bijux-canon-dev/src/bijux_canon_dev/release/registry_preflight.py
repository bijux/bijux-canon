"""Perform authenticated, fail-closed release identity collision checks."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
import time
from typing import cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bijux_canon_dev.release.python_support_matrix import CommandResult, CommandRunner


class RegistryPreflightError(RuntimeError):
    """A live registry query could not establish collision state."""


PyPIProbe = Callable[[str, str], dict[str, object]]


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise RegistryPreflightError("registry commands require an absolute executable")
    started = time.monotonic()
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(environment),
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        command=tuple(command),
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=time.monotonic() - started,
    )


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def probe_pypi(distribution_name: str, version: str) -> dict[str, object]:
    """Return exact-version availability from PyPI's authoritative JSON API."""
    url = f"https://pypi.org/pypi/{quote(distribution_name, safe='')}/{version}/json"
    request = Request(url, headers={"Accept": "application/json"})
    checked_at = datetime.now(UTC).isoformat()
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            status_code = response.status
    except HTTPError as exc:
        status_code = exc.code
    except (OSError, URLError) as exc:
        return {
            "distribution_name": distribution_name,
            "version": version,
            "url": url,
            "checked_at": checked_at,
            "status": "indeterminate",
            "error": str(exc),
        }
    if status_code == 200:
        status = "collision"
    elif status_code == 404:
        status = "unused"
    else:
        status = "indeterminate"
    return {
        "distribution_name": distribution_name,
        "version": version,
        "url": url,
        "checked_at": checked_at,
        "http_status": status_code,
        "status": status,
    }


def _lines(result: CommandResult) -> tuple[str, ...]:
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def run_registry_preflight(
    *,
    repo_root: Path,
    version: str,
    tag: str,
    package_names: Sequence[str],
    container_names: Sequence[str],
    github_repository: str,
    remote: str,
    git_executable: Path,
    gh_executable: Path,
    runner: CommandRunner = _default_runner,
    pypi_probe: PyPIProbe = probe_pypi,
) -> dict[str, object]:
    """Prove a version is unused across remote Git, GitHub, PyPI, and GHCR."""
    repo_root = repo_root.resolve()
    repository_parts = github_repository.split("/")
    if len(repository_parts) != 2 or not all(repository_parts):
        raise RegistryPreflightError("GitHub repository must use owner/name")
    owner, repository = repository_parts
    if not remote or not package_names:
        raise RegistryPreflightError("remote and package inventory must be nonempty")
    if len(package_names) != len(set(package_names)):
        raise RegistryPreflightError("PyPI package inventory contains duplicates")
    if not set(container_names).issubset(package_names):
        raise RegistryPreflightError("container inventory must be a package subset")

    environment = dict(os.environ)
    environment["GH_PROMPT_DISABLED"] = "1"
    commands: list[CommandResult] = []

    def execute(command: Sequence[str]) -> CommandResult:
        outcome = runner(command, repo_root, environment)
        commands.append(outcome)
        return outcome

    remote_tag = execute(
        [
            str(git_executable.resolve()),
            "ls-remote",
            "--tags",
            "--refs",
            remote,
            f"refs/tags/{tag}",
        ]
    )
    owner_type = execute(
        [str(gh_executable.resolve()), "api", f"users/{owner}", "--jq", ".type"]
    )
    viewer = execute(
        [str(gh_executable.resolve()), "api", "user", "--jq", ".login"]
    )
    repository_access = execute(
        [
            str(gh_executable.resolve()),
            "api",
            f"repos/{owner}/{repository}",
            "--jq",
            ".permissions.push",
        ]
    )
    releases = execute(
        [
            str(gh_executable.resolve()),
            "api",
            "--paginate",
            f"repos/{owner}/{repository}/releases?per_page=100",
            "--jq",
            f'.[] | select(.tag_name == "{tag}") | [.tag_name, .draft, .html_url] | @tsv',
        ]
    )

    failures: list[str] = []
    if remote_tag.exit_code != 0:
        failures.append("remote-tag-indeterminate")
    elif _lines(remote_tag):
        failures.append(f"remote-tag-collision:{tag}")
    if owner_type.exit_code != 0 or _lines(owner_type) not in {
        ("User",),
        ("Organization",),
    }:
        failures.append("github-owner-type-indeterminate")
        owner_kind = ""
    else:
        owner_kind = _lines(owner_type)[0]
    if viewer.exit_code != 0 or len(_lines(viewer)) != 1:
        failures.append("github-viewer-indeterminate")
        viewer_login = ""
    else:
        viewer_login = _lines(viewer)[0]
    if owner_kind == "User" and viewer_login.casefold() != owner.casefold():
        failures.append("github-user-package-visibility-unproven")
    if repository_access.exit_code != 0 or _lines(repository_access) != ("true",):
        failures.append("github-draft-visibility-unproven")
    if releases.exit_code != 0:
        failures.append("github-releases-indeterminate")
    elif _lines(releases):
        failures.append(f"github-release-collision:{tag}")

    package_listing: CommandResult | None = None
    container_results: list[dict[str, object]] = []
    if owner_kind and not (
        owner_kind == "User" and viewer_login.casefold() != owner.casefold()
    ):
        owner_segment = "user" if owner_kind == "User" else f"orgs/{owner}"
        package_listing = execute(
            [
                str(gh_executable.resolve()),
                "api",
                "--paginate",
                f"{owner_segment}/packages?package_type=container&per_page=100",
                "--jq",
                f'.[] | .name | select(startswith("{repository}/"))',
            ]
        )
        if package_listing.exit_code != 0:
            failures.append("ghcr-inventory-indeterminate")
        else:
            visible_packages = set(_lines(package_listing))
            for distribution_name in container_names:
                package_name = f"{repository}/{distribution_name}"
                if package_name not in visible_packages:
                    container_results.append(
                        {
                            "distribution_name": distribution_name,
                            "package_name": package_name,
                            "tag": tag,
                            "status": "unused",
                            "reason": "package-absent-from-authenticated-inventory",
                        }
                    )
                    continue
                versions = execute(
                    [
                        str(gh_executable.resolve()),
                        "api",
                        "--paginate",
                        f"{owner_segment}/packages/container/{quote(package_name, safe='')}/versions?per_page=100",
                        "--jq",
                        f'.[] | select(any(.metadata.container.tags[]?; . == "{tag}")) | [.id, (.metadata.container.tags | join(","))] | @tsv',
                    ]
                )
                if versions.exit_code != 0:
                    status = "indeterminate"
                    failures.append(f"ghcr-indeterminate:{package_name}")
                elif _lines(versions):
                    status = "collision"
                    failures.append(f"ghcr-collision:{package_name}:{tag}")
                else:
                    status = "unused"
                container_results.append(
                    {
                        "distribution_name": distribution_name,
                        "package_name": package_name,
                        "tag": tag,
                        "status": status,
                        "query": _command_payload(versions),
                    }
                )

    with ThreadPoolExecutor(max_workers=min(8, len(package_names))) as executor:
        pypi_results = list(
            executor.map(
                lambda name: pypi_probe(name, version),
                package_names,
            )
        )
    for result in pypi_results:
        pypi_status = result.get("status")
        name = cast(str, result.get("distribution_name", "unknown"))
        if pypi_status == "collision":
            failures.append(f"pypi-collision:{name}:{version}")
        elif pypi_status != "unused":
            failures.append(f"pypi-indeterminate:{name}:{version}")

    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not failures else "failed",
        "version": version,
        "tag": tag,
        "github_repository": github_repository,
        "remote": remote,
        "remote_tag": {
            "status": (
                "indeterminate"
                if remote_tag.exit_code != 0
                else "collision"
                if _lines(remote_tag)
                else "unused"
            ),
            "query": _command_payload(remote_tag),
        },
        "github_releases": {
            "draft_visibility": repository_access.exit_code == 0
            and _lines(repository_access) == ("true",),
            "status": (
                "indeterminate"
                if releases.exit_code != 0
                else "collision"
                if _lines(releases)
                else "unused"
            ),
            "query": _command_payload(releases),
        },
        "pypi": pypi_results,
        "ghcr_inventory_query": (
            _command_payload(package_listing) if package_listing is not None else None
        ),
        "ghcr": container_results,
        "commands": [_command_payload(command) for command in commands],
        "retained_failures": sorted(set(failures)),
    }
