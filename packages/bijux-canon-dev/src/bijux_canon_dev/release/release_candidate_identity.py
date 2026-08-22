"""Bind a proposed release tag to source, package, lock, and wheel identities."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time
import tomllib

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from bijux_canon_dev.release.python_support_matrix import (
    CommandResult,
    CommandRunner,
    WheelRecord,
    inspect_wheels,
)
from bijux_canon_dev.release.wheel_inventory import inspect_workspace_policy


class ReleaseCandidateIdentityError(RuntimeError):
    """The proposed tag cannot identify one complete local release candidate."""


@dataclass(frozen=True)
class CandidatePackage:
    """Source metadata that must agree for one candidate distribution."""

    distribution_name: str
    package_key: str | None
    package_class: str
    pyproject_path: Path
    changelog_path: Path
    fallback_version: str | None
    changelog_has_version: bool


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise ReleaseCandidateIdentityError(
            "release-candidate commands require an absolute executable"
        )
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


def _artifact_path(path: Path, repo_root: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to((repo_root / "artifacts").resolve())
    except ValueError as exc:
        raise ReleaseCandidateIdentityError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def validate_release_tag(tag: str) -> str:
    """Return the normalized stable version named by an exact ``v`` tag."""
    if re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) is None:
        raise ReleaseCandidateIdentityError("release tag must use the form vX.Y.Z")
    candidate = tag.removeprefix("v")
    try:
        version = Version(candidate)
    except InvalidVersion as exc:
        raise ReleaseCandidateIdentityError(f"invalid release tag: {tag}") from exc
    if (
        str(version) != candidate
        or version.is_prerelease
        or version.is_devrelease
        or version.local is not None
    ):
        raise ReleaseCandidateIdentityError(
            f"release tag must name one normalized stable version: {tag}"
        )
    return candidate


def _changelog_has_version(text: str, version: str) -> bool:
    heading = re.compile(
        rf"^##\s+(?:\[)?{re.escape(version)}(?:\])?(?:\s+[-–—].*)?$",
        re.MULTILINE,
    )
    return heading.search(text) is not None


def _candidate_packages(repo_root: Path, version: str) -> tuple[CandidatePackage, ...]:
    packages: list[CandidatePackage] = []
    for policy in inspect_workspace_policy(repo_root):
        data = tomllib.loads(policy.pyproject_path.read_text(encoding="utf-8"))
        fallback = (
            data.get("tool", {})
            .get("hatch", {})
            .get("version", {})
            .get("fallback-version")
        )
        changelog = policy.pyproject_path.parent / "CHANGELOG.md"
        packages.append(
            CandidatePackage(
                distribution_name=policy.distribution_name,
                package_key=policy.package_key,
                package_class=policy.package_class,
                pyproject_path=policy.pyproject_path,
                changelog_path=changelog,
                fallback_version=fallback if isinstance(fallback, str) else None,
                changelog_has_version=(
                    changelog.is_file()
                    and _changelog_has_version(
                        changelog.read_text(encoding="utf-8"), version
                    )
                ),
            )
        )
    return tuple(packages)


def analyze_release_candidate(
    *,
    version: str,
    packages: Sequence[CandidatePackage],
    wheels: Sequence[WheelRecord],
) -> tuple[dict[str, object], ...]:
    """Require exact source and built versions for the complete inventory."""
    package_by_name = {
        str(canonicalize_name(package.distribution_name)): package
        for package in packages
    }
    wheel_by_name = {
        str(canonicalize_name(wheel.distribution_name)): wheel for wheel in wheels
    }
    if set(package_by_name) != set(wheel_by_name):
        raise ReleaseCandidateIdentityError(
            "candidate source and wheel distribution inventories disagree"
        )

    failures: list[str] = []
    results: list[dict[str, object]] = []
    for name, package in sorted(package_by_name.items()):
        wheel = wheel_by_name[name]
        issues: list[str] = []
        if package.fallback_version != version:
            issues.append(f"fallback-version={package.fallback_version!r}")
        if not package.changelog_has_version:
            issues.append("missing-candidate-changelog")
        if wheel.version != version:
            issues.append(f"wheel-version={wheel.version!r}")
        if issues:
            failures.extend(f"{name}:{issue}" for issue in issues)
        results.append(
            {
                "distribution_name": package.distribution_name,
                "package_key": package.package_key,
                "package_class": package.package_class,
                "fallback_version": package.fallback_version,
                "wheel_version": wheel.version,
                "wheel": wheel.path.name,
                "wheel_sha256": wheel.sha256,
                "changelog_has_version": package.changelog_has_version,
                "status": "passed" if not issues else "failed",
                "issues": issues,
            }
        )
    if failures:
        raise ReleaseCandidateIdentityError(
            "release candidate identities disagree: " + ", ".join(failures)
        )
    return tuple(results)


def _git_context(repo_root: Path, tag: str) -> tuple[str, list[CommandResult]]:
    git_value = shutil.which("git")
    if git_value is None:
        raise ReleaseCandidateIdentityError("git executable not found")
    git = str(Path(git_value).resolve())
    environment = dict(os.environ)
    commands = (
        (git, "status", "--porcelain=v1"),
        (git, "rev-parse", "HEAD"),
        (git, "check-ref-format", f"refs/tags/{tag}"),
        (git, "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"),
    )
    outcomes = [
        _default_runner(command, repo_root, environment) for command in commands
    ]
    if outcomes[0].exit_code != 0 or outcomes[0].stdout.strip():
        raise ReleaseCandidateIdentityError(
            "release candidate requires a clean source checkout"
        )
    if outcomes[1].exit_code != 0:
        raise ReleaseCandidateIdentityError("cannot resolve release target commit")
    if outcomes[2].exit_code != 0:
        raise ReleaseCandidateIdentityError(f"invalid Git tag reference: {tag}")
    if outcomes[3].exit_code == 0:
        raise ReleaseCandidateIdentityError(
            f"proposed tag already exists; no tag was created: {tag}"
        )
    if outcomes[3].exit_code != 1:
        raise ReleaseCandidateIdentityError("cannot determine proposed tag state")
    return outcomes[1].stdout.strip(), outcomes


def run_release_candidate_identity(
    *,
    repo_root: Path,
    wheel_dir: Path,
    output_path: Path,
    tag: str,
    target_commit: str,
    uv_executable: Path,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Validate an uncreated tag against current source and candidate wheels."""
    repo_root = repo_root.resolve()
    wheel_dir = _artifact_path(wheel_dir, repo_root, label="wheel directory")
    output_path = _artifact_path(output_path, repo_root, label="output path")
    version = validate_release_tag(tag)
    source_commit, git_outcomes = _git_context(repo_root, tag)
    if target_commit != source_commit or len(target_commit) != 40:
        raise ReleaseCandidateIdentityError(
            "proposed tag target must be the current full source commit"
        )

    packages = _candidate_packages(repo_root, version)
    wheels = inspect_wheels(
        wheel_dir, tuple(package.distribution_name for package in packages)
    )
    package_records = analyze_release_candidate(
        version=version,
        packages=packages,
        wheels=wheels,
    )
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(output_path.parent / "cache" / "pycache"),
            "UV_CACHE_DIR": str(output_path.parent / "cache" / "uv"),
        }
    )
    lock_check = runner(
        [str(uv_executable.resolve()), "lock", "--check"], repo_root, environment
    )
    failures = [] if lock_check.exit_code == 0 else ["lock-check"]
    package_results = [
        {
            "package_id": record["distribution_name"],
            "package_class": record["package_class"],
            "status": record["status"],
        }
        for record in package_records
        if record["package_key"] is not None
    ]
    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.release_candidate_identity.v1",
        "source_commit": source_commit,
        "created_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not failures else "failed",
        "environment": {
            "platform": platform.platform(),
            "runner_python": platform.python_version(),
        },
        "proposed_tag": tag,
        "proposed_target_commit": target_commit,
        "tag_created": False,
        "candidate_version": version,
        "git_commands": [_command_payload(outcome) for outcome in git_outcomes],
        "lock": {
            "path": "uv.lock",
            "sha256": _sha256(repo_root / "uv.lock"),
            "check": _command_payload(lock_check),
        },
        "wheel_directory": wheel_dir.relative_to(repo_root).as_posix(),
        "wheel_count": len(wheels),
        "package_identities": list(package_records),
        "package_results": package_results,
        "retained_failures": failures,
        "limitations": [
            "the tag and registry publication remain explicit external actions",
            "remote registry availability is not inferred from local candidate proof",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        raise ReleaseCandidateIdentityError(
            f"release candidate validation failed; inspect {output_path}"
        )
    return evidence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bind an uncreated release tag to source, lock, and wheels."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--target-commit")
    parser.add_argument("--uv", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed release-candidate identity verifier."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    git = shutil.which("git")
    uv = args.uv or (Path(value) if (value := shutil.which("uv")) else None)
    if git is None:
        raise SystemExit("git executable not found")
    if uv is None:
        raise SystemExit("uv executable not found; provide --uv")
    head = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if head.returncode != 0:
        raise SystemExit(head.stderr.strip() or "git rev-parse failed")
    try:
        run_release_candidate_identity(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            output_path=args.output,
            tag=args.tag,
            target_commit=args.target_commit or head.stdout.strip(),
            uv_executable=uv,
        )
    except ReleaseCandidateIdentityError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
