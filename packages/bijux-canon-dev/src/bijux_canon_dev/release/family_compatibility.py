"""Verify exact-version package-family dependencies and publication order."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from bijux_canon_dev.release.installation_matrix import (
    InstallationMatrixError,
    _dependency_wheels,
)
from bijux_canon_dev.release.python_support_matrix import (
    CommandResult,
    CommandRunner,
    WheelRecord,
    inspect_wheels,
    inspect_workspace,
)
from bijux_canon_dev.release.wheel_inventory import inspect_workspace_policy


class FamilyCompatibilityError(RuntimeError):
    """The release family can resolve to an untested version combination."""


@dataclass(frozen=True)
class FamilyWheel:
    """Dependency metadata needed to analyze one release-family wheel."""

    distribution_name: str
    version: str
    requirements: tuple[str, ...]


@dataclass(frozen=True)
class FamilyEdge:
    """One exact-version dependency inside the public release family."""

    consumer: str
    provider: str
    requirement: str


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise FamilyCompatibilityError(
            "family compatibility commands require an absolute executable"
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
        raise FamilyCompatibilityError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def _python_path(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


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


def _wheel_requirements(path: Path) -> tuple[str, ...]:
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        if len(names) != 1:
            raise FamilyCompatibilityError(
                f"wheel must contain exactly one METADATA file: {path.name}"
            )
        message = BytesParser().parsebytes(archive.read(names[0]))
    return tuple(sorted(message.get_all("Requires-Dist", [])))


def _workspace_release_policy(
    repo_root: Path,
) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    workspace = data.get("tool", {}).get("bijux_canon", {})
    public = workspace.get("public_release_packages")
    package_dirs = workspace.get("package_dirs")
    tiers = workspace.get("release_publication_tiers")
    if not isinstance(public, list) or not all(
        isinstance(item, str) for item in public
    ):
        raise FamilyCompatibilityError("public_release_packages must be a string list")
    if not isinstance(package_dirs, dict):
        raise FamilyCompatibilityError("package_dirs must be a table")
    if not isinstance(tiers, list) or not all(
        isinstance(tier, list) and tier and all(isinstance(item, str) for item in tier)
        for tier in tiers
    ):
        raise FamilyCompatibilityError(
            "release_publication_tiers must contain nonempty string lists"
        )
    names: list[str] = []
    for package_key in public:
        path_value = package_dirs.get(package_key)
        if not isinstance(path_value, str):
            raise FamilyCompatibilityError(
                f"public package has no package directory: {package_key}"
            )
        package_data = tomllib.loads(
            (repo_root / path_value / "pyproject.toml").read_text(encoding="utf-8")
        )
        name = package_data.get("project", {}).get("name")
        if not isinstance(name, str) or not name:
            raise FamilyCompatibilityError(
                f"public package has no distribution name: {package_key}"
            )
        names.append(canonicalize_name(name))
    normalized_tiers = tuple(
        tuple(
            canonicalize_name(
                tomllib.loads(
                    (
                        repo_root / str(package_dirs[package_key]) / "pyproject.toml"
                    ).read_text(encoding="utf-8")
                )["project"]["name"]
            )
            for package_key in tier
        )
        for tier in tiers
    )
    return tuple(names), normalized_tiers


def analyze_family(
    *,
    wheels: Sequence[FamilyWheel],
    public_distributions: Sequence[str],
    publication_tiers: Sequence[Sequence[str]],
    expected_edges: Sequence[tuple[str, str]],
    previous_version: str,
) -> tuple[tuple[FamilyEdge, ...], tuple[dict[str, object], ...]]:
    """Validate exact peer pins, a topological publication order, and transitions."""
    public = {str(canonicalize_name(name)) for name in public_distributions}
    wheel_by_name = {
        str(canonicalize_name(wheel.distribution_name)): wheel for wheel in wheels
    }
    if public != set(wheel_by_name):
        raise FamilyCompatibilityError(
            "public release wheel inventory does not match publication policy"
        )
    versions = {wheel.version for wheel in wheels}
    if len(versions) != 1:
        raise FamilyCompatibilityError(f"public wheel versions disagree: {versions}")
    version = next(iter(versions))
    if previous_version == version:
        raise FamilyCompatibilityError(
            "previous version must differ from the candidate"
        )

    edges: list[FamilyEdge] = []
    for wheel in wheels:
        consumer = str(canonicalize_name(wheel.distribution_name))
        for value in wheel.requirements:
            requirement = Requirement(value)
            provider = str(canonicalize_name(requirement.name))
            if provider not in public:
                continue
            if (
                requirement.url is not None
                or requirement.marker is not None
                or requirement.extras
                or str(requirement.specifier) != f"=={version}"
            ):
                raise FamilyCompatibilityError(
                    f"internal dependency must use the candidate's exact version: "
                    f"{consumer} -> {value}"
                )
            edges.append(FamilyEdge(consumer, provider, value))

    expected = {
        (str(canonicalize_name(consumer)), str(canonicalize_name(provider)))
        for consumer, provider in expected_edges
    }
    actual = {(edge.consumer, edge.provider) for edge in edges}
    if actual != expected:
        raise FamilyCompatibilityError(
            f"family dependency edges disagree; missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )

    flattened = [
        str(canonicalize_name(name)) for tier in publication_tiers for name in tier
    ]
    if len(flattened) != len(set(flattened)) or set(flattened) != public:
        raise FamilyCompatibilityError(
            "publication tiers must partition the public release distributions"
        )
    tier_by_name = {
        str(canonicalize_name(name)): index
        for index, tier in enumerate(publication_tiers)
        for name in tier
    }
    unordered = [
        edge
        for edge in edges
        if tier_by_name[edge.provider] >= tier_by_name[edge.consumer]
    ]
    if unordered:
        raise FamilyCompatibilityError(
            f"publication order violates dependency direction: {unordered}"
        )

    combinations: list[dict[str, object]] = []
    for edge in sorted(edges, key=lambda item: (item.consumer, item.provider)):
        current = Requirement(edge.requirement).specifier
        previous = SpecifierSet(f"=={previous_version}")
        cases = (
            ("current-current", version, version, current.contains(version)),
            (
                "current-previous",
                version,
                previous_version,
                current.contains(previous_version),
            ),
            (
                "previous-current",
                previous_version,
                version,
                previous.contains(version),
            ),
        )
        for case_id, consumer_version, provider_version, supported in cases:
            expected_support = case_id == "current-current"
            if supported != expected_support:
                raise FamilyCompatibilityError(
                    f"unexpected compatibility for {edge.consumer}->{edge.provider} "
                    f"in {case_id}"
                )
            combinations.append(
                {
                    "combination_id": (f"{edge.consumer}--{edge.provider}--{case_id}"),
                    "consumer": edge.consumer,
                    "consumer_version": consumer_version,
                    "provider": edge.provider,
                    "provider_version": provider_version,
                    "supported": supported,
                    "expected_supported": expected_support,
                    "status": "passed",
                }
            )
    return tuple(edges), tuple(combinations)


def _expected_edges(repo_root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                canonicalize_name(policy.distribution_name),
                canonicalize_name(provider),
            )
            for policy in inspect_workspace_policy(repo_root)
            for provider in policy.dynamic_dependency_names
        )
    )


def _inspector(
    *,
    records: Sequence[WheelRecord],
    public: Sequence[str],
    source_roots: Sequence[Path],
) -> str:
    public_set = {canonicalize_name(name) for name in public}
    versions = {
        record.distribution_name: record.version
        for record in records
        if canonicalize_name(record.distribution_name) in public_set
    }
    imports = tuple(
        sorted(
            {
                name
                for record in records
                if canonicalize_name(record.distribution_name) in public_set
                for name in record.import_names
            }
        )
    )
    return "\n".join(
        [
            "import importlib",
            "import importlib.metadata as metadata",
            "import json",
            "from pathlib import Path",
            "import sysconfig",
            f"versions = {versions!r}",
            f"imports = {imports!r}",
            f"source_roots = tuple(Path(value).resolve() for value in {tuple(map(str, source_roots))!r})",
            "purelib = Path(sysconfig.get_paths()['purelib']).resolve()",
            "installed = {name: metadata.version(name) for name in versions}",
            "assert installed == versions, (installed, versions)",
            "origins = {}",
            "for name in imports:",
            "    module = importlib.import_module(name)",
            "    origin = Path(module.__file__).resolve()",
            "    assert origin.is_relative_to(purelib), (name, origin, purelib)",
            "    assert not any(origin.is_relative_to(root) for root in source_roots), (name, origin)",
            "    origins[name] = str(origin)",
            "print(json.dumps({'versions': installed, 'module_origins': origins}, sort_keys=True))",
        ]
    )


def run_family_compatibility(
    *,
    repo_root: Path,
    wheel_dir: Path,
    dependency_wheel_dir: Path,
    output_path: Path,
    environment_root: Path,
    source_commit: str,
    previous_version: str,
    python_version: str,
    uv_executable: Path,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Validate metadata policy and install the exact public wheel family."""
    repo_root = repo_root.resolve()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise FamilyCompatibilityError("source commit must be a lowercase full Git SHA")
    wheel_dir = _artifact_path(wheel_dir, repo_root, label="wheel directory")
    dependency_wheel_dir = _artifact_path(
        dependency_wheel_dir, repo_root, label="dependency wheel directory"
    )
    output_path = _artifact_path(output_path, repo_root, label="output path")
    environment_root = _artifact_path(
        environment_root, repo_root, label="environment root"
    )
    support = inspect_workspace(repo_root)
    records = inspect_wheels(wheel_dir, support.distribution_names)
    try:
        dependency_wheels = _dependency_wheels(
            dependency_wheel_dir,
            candidate_names=[record.distribution_name for record in records],
        )
    except InstallationMatrixError as exc:
        raise FamilyCompatibilityError(str(exc)) from exc
    public, tiers = _workspace_release_policy(repo_root)
    public_set = set(public)
    public_records = tuple(
        record
        for record in records
        if canonicalize_name(record.distribution_name) in public_set
    )
    wheels = tuple(
        FamilyWheel(
            record.distribution_name,
            record.version,
            _wheel_requirements(record.path),
        )
        for record in public_records
    )
    edges, combinations = analyze_family(
        wheels=wheels,
        public_distributions=public,
        publication_tiers=tiers,
        expected_edges=_expected_edges(repo_root),
        previous_version=previous_version,
    )

    environment_root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    constraints = environment_root.parent / "candidate-constraints.txt"
    constraints.write_text(
        "".join(
            f"{record.distribution_name}=={record.version}\n" for record in records
        ),
        encoding="utf-8",
    )
    python = _python_path(environment_root)
    source_roots = tuple(
        (policy.pyproject_path.parent / "src").resolve()
        for policy in inspect_workspace_policy(repo_root)
        if policy.package_key is not None
    )
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(output_path.parent / "cache" / "pycache"),
            "UV_CACHE_DIR": str(output_path.parent / "cache" / "uv"),
            "UV_NO_INDEX": "1",
        }
    )
    commands = [
        [
            str(uv_executable.absolute()),
            "venv",
            str(environment_root),
            "--python",
            python_version,
            "--clear",
        ],
        [
            str(uv_executable.absolute()),
            "pip",
            "install",
            "--no-index",
            "--python",
            str(python),
            "--constraint",
            str(constraints),
            "--find-links",
            str(wheel_dir),
            "--find-links",
            str(dependency_wheel_dir),
            *[str(record.path) for record in public_records],
        ],
        [str(uv_executable.absolute()), "pip", "check", "--python", str(python)],
        [
            str(python),
            "-I",
            "-c",
            _inspector(records=records, public=public, source_roots=source_roots),
        ],
    ]
    outcomes: list[CommandResult] = []
    for command in commands:
        outcome = runner(command, output_path.parent, environment)
        outcomes.append(outcome)
        if outcome.exit_code != 0:
            break
    failures = []
    if len(outcomes) != len(commands) or any(
        outcome.exit_code != 0 for outcome in outcomes
    ):
        failures.append("installed-public-family")

    package_class_by_name = dict(support.package_classes)
    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.family_compatibility.v1",
        "source_commit": source_commit,
        "created_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not failures else "failed",
        "environment": {
            "platform": platform.platform(),
            "runner_python": platform.python_version(),
            "requested_python": python_version,
        },
        "candidate_version": public_records[0].version,
        "previous_version": previous_version,
        "public_distributions": list(public),
        "publication_tiers": [list(tier) for tier in tiers],
        "dependency_edges": [
            {
                "consumer": edge.consumer,
                "provider": edge.provider,
                "requirement": edge.requirement,
            }
            for edge in edges
        ],
        "compatibility_combinations": list(combinations),
        "installation": {
            "constraint_file": constraints.relative_to(repo_root).as_posix(),
            "commands": [_command_payload(outcome) for outcome in outcomes],
            "status": "passed" if not failures else "failed",
        },
        "wheel_hashes": {
            record.distribution_name: record.sha256 for record in public_records
        },
        "dependency_wheel_directory": dependency_wheel_dir.relative_to(
            repo_root
        ).as_posix(),
        "dependency_wheel_count": len(dependency_wheels),
        "dependency_wheels": list(dependency_wheels),
        "public_index_access": False,
        "lock_identity": _sha256(repo_root / "uv.lock"),
        "package_results": [
            {
                "package_id": name,
                "package_class": package_class_by_name[name],
                "status": "passed" if not failures else "failed",
            }
            for name in sorted(package_class_by_name, key=canonicalize_name)
        ],
        "retained_failures": failures,
        "limitations": [
            "historical wheel behavior remains governed by its published metadata",
            "cross-platform installation remains owned by remote package verification",
        ],
    }
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        raise FamilyCompatibilityError(
            f"family installation failed; inspect {output_path}"
        )
    return evidence


def _git_identity(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise FamilyCompatibilityError("git executable not found")
    status = subprocess.run(
        [git, "status", "--porcelain=v1"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise FamilyCompatibilityError(status.stderr.strip() or "git status failed")
    if status.stdout.strip():
        raise FamilyCompatibilityError(
            "family compatibility requires a clean source checkout"
        )
    identity = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise FamilyCompatibilityError(
            identity.stderr.strip() or "git rev-parse failed"
        )
    return identity.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify exact release-family dependencies, publication order, and install."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--dependency-wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--previous-version", required=True)
    parser.add_argument(
        "--python-version",
        default=f"{sys.version_info.major}.{sys.version_info.minor}",
    )
    parser.add_argument("--uv", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed release-family compatibility verifier."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    uv = args.uv or (Path(value) if (value := shutil.which("uv")) else None)
    if uv is None:
        raise SystemExit("uv executable not found; provide --uv")
    try:
        run_family_compatibility(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            dependency_wheel_dir=args.dependency_wheel_dir,
            output_path=args.output,
            environment_root=args.environment_root,
            source_commit=_git_identity(repo_root),
            previous_version=args.previous_version,
            python_version=args.python_version,
            uv_executable=uv,
        )
    except FamilyCompatibilityError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
