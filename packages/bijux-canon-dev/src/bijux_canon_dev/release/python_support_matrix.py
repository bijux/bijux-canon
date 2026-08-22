"""Verify the complete workspace wheel set on every advertised Python version."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import configparser
from dataclasses import dataclass
from datetime import UTC, datetime
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import time
import tomllib
from typing import Any, cast
import zipfile

from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


class PythonSupportVerificationError(RuntimeError):
    """The declared Python support or its installed-wheel proof is invalid."""


@dataclass(frozen=True)
class WorkspaceSupport:
    """Python versions and distributions declared by the workspace."""

    python_versions: tuple[str, ...]
    distribution_names: tuple[str, ...]
    pyproject_paths: tuple[Path, ...]
    package_classes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class WheelRecord:
    """Security-relevant metadata read directly from one wheel."""

    path: Path
    distribution_name: str
    version: str
    requires_python: str
    import_names: tuple[str, ...]
    console_scripts: tuple[str, ...]
    sha256: str
    byte_length: int


@dataclass(frozen=True)
class CommandResult:
    """One isolated command outcome retained in the matrix evidence."""

    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], CommandResult]

_PYTHON_CLASSIFIER = "Programming Language :: Python :: "


def _load_pyproject(path: Path) -> dict[str, Any]:
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise PythonSupportVerificationError(f"cannot read {path}: {exc}") from exc
    return value


def _classifier_versions(project: Mapping[str, object]) -> tuple[str, ...]:
    classifiers = project.get("classifiers", [])
    if not isinstance(classifiers, list):
        raise PythonSupportVerificationError("project classifiers must be a list")
    versions = {
        item.removeprefix(_PYTHON_CLASSIFIER)
        for item in classifiers
        if isinstance(item, str)
        and item.startswith(_PYTHON_CLASSIFIER + "3.")
        and item.removeprefix(_PYTHON_CLASSIFIER).count(".") == 1
    }
    return tuple(sorted(versions, key=lambda value: tuple(map(int, value.split(".")))))


def inspect_workspace(repo_root: Path) -> WorkspaceSupport:
    """Derive and cross-check the workspace's advertised Python support."""
    repo_root = repo_root.resolve()
    root_pyproject = repo_root / "pyproject.toml"
    root_data = _load_pyproject(root_pyproject)
    workspace = cast(
        dict[str, Any],
        cast(dict[str, Any], root_data.get("tool", {})).get("bijux_canon", {}),
    )
    package_dirs = workspace.get("package_dirs")
    if not isinstance(package_dirs, dict) or not package_dirs:
        raise PythonSupportVerificationError(
            "tool.bijux_canon.package_dirs must declare the workspace packages"
        )
    primary_packages = workspace.get("primary_packages")
    compatibility_packages = workspace.get("compat_packages")
    if not isinstance(primary_packages, list) or not all(
        isinstance(value, str) for value in primary_packages
    ):
        raise PythonSupportVerificationError(
            "tool.bijux_canon.primary_packages must be a string list"
        )
    if not isinstance(compatibility_packages, list) or not all(
        isinstance(value, str) for value in compatibility_packages
    ):
        raise PythonSupportVerificationError(
            "tool.bijux_canon.compat_packages must be a string list"
        )
    primary_set = set(primary_packages)
    compatibility_set = set(compatibility_packages)
    package_keys = set(package_dirs)
    if (
        primary_set & compatibility_set
        or primary_set | compatibility_set != package_keys
    ):
        raise PythonSupportVerificationError(
            "primary and compatibility package inventories must partition package_dirs"
        )

    pyprojects = [root_pyproject]
    package_class_by_path: dict[Path, str] = {}
    for package_key, value in package_dirs.items():
        if not isinstance(value, str):
            raise PythonSupportVerificationError(
                "workspace package path must be a string"
            )
        path = (repo_root / value / "pyproject.toml").resolve()
        try:
            path.relative_to(repo_root)
        except ValueError as exc:
            raise PythonSupportVerificationError(
                f"workspace package escapes repository: {value}"
            ) from exc
        pyprojects.append(path)
        package_class_by_path[path] = (
            "canonical" if package_key in primary_set else "compatibility"
        )

    distribution_names: list[str] = []
    declared_version_sets: dict[Path, tuple[str, ...]] = {}
    package_classes: list[tuple[str, str]] = []
    projects: list[tuple[Path, Mapping[str, object]]] = []
    for path in pyprojects:
        data = _load_pyproject(path)
        project = data.get("project")
        if not isinstance(project, dict):
            raise PythonSupportVerificationError(f"missing project table in {path}")
        name = project.get("name")
        requires_python = project.get("requires-python")
        if not isinstance(name, str) or not name:
            raise PythonSupportVerificationError(f"missing project name in {path}")
        if not isinstance(requires_python, str) or not requires_python:
            raise PythonSupportVerificationError(f"missing requires-python in {path}")
        distribution_names.append(name)
        projects.append((path, cast(Mapping[str, object], project)))
        versions = _classifier_versions(cast(Mapping[str, object], project))
        if path != root_pyproject:
            if not versions:
                raise PythonSupportVerificationError(
                    f"no minor Python classifiers declared in {path}"
                )
            declared_version_sets[path] = versions
            classifiers = project.get("classifiers", [])
            if "Operating System :: OS Independent" not in classifiers:
                raise PythonSupportVerificationError(
                    f"package does not declare its platform promise in {path}"
                )
            package_classes.append((name, package_class_by_path[path]))

    distinct_version_sets = set(declared_version_sets.values())
    if len(distinct_version_sets) != 1:
        details = ", ".join(
            f"{path.parent.name}={','.join(versions)}"
            for path, versions in sorted(declared_version_sets.items())
        )
        raise PythonSupportVerificationError(
            f"workspace Python classifier sets disagree: {details}"
        )
    python_versions = next(iter(distinct_version_sets))
    for path, project in projects:
        specifier = SpecifierSet(cast(str, project["requires-python"]))
        unsupported = [
            version for version in python_versions if not specifier.contains(version)
        ]
        if unsupported:
            raise PythonSupportVerificationError(
                f"{path} classifiers contradict requires-python for {unsupported}"
            )

    canonical_names = [canonicalize_name(name) for name in distribution_names]
    if len(canonical_names) != len(set(canonical_names)):
        raise PythonSupportVerificationError(
            "workspace distribution names must be unique after normalization"
        )
    return WorkspaceSupport(
        python_versions=python_versions,
        distribution_names=tuple(sorted(distribution_names, key=canonicalize_name)),
        pyproject_paths=tuple(pyprojects),
        package_classes=tuple(
            sorted(package_classes, key=lambda item: canonicalize_name(item[0]))
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_wheel_members(archive: zipfile.ZipFile, wheel: Path) -> list[str]:
    members: list[str] = []
    for info in archive.infolist():
        name = info.filename
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts or "\\" in name:
            raise PythonSupportVerificationError(
                f"unsafe member in wheel {wheel.name}: {name}"
            )
        members.append(name)
    return members


def _wheel_metadata(
    archive: zipfile.ZipFile, members: Sequence[str], wheel: Path
) -> tuple[str, str, str]:
    metadata_members = [
        name for name in members if name.endswith(".dist-info/METADATA")
    ]
    if len(metadata_members) != 1:
        raise PythonSupportVerificationError(
            f"wheel must contain exactly one METADATA file: {wheel}"
        )
    metadata = BytesParser().parsebytes(archive.read(metadata_members[0]))
    name = metadata.get("Name")
    version = metadata.get("Version")
    requires_python = metadata.get("Requires-Python")
    if not name or not version or not requires_python:
        raise PythonSupportVerificationError(
            f"wheel metadata lacks Name, Version, or Requires-Python: {wheel}"
        )
    return name, version, requires_python


def _wheel_imports(members: Sequence[str]) -> tuple[str, ...]:
    imports: set[str] = set()
    for name in members:
        parts = PurePosixPath(name).parts
        if not parts or ".dist-info" in parts[0] or ".data" in parts[0]:
            continue
        first = parts[0]
        if len(parts) == 1 and first.endswith(".py"):
            first = first[:-3]
        if first.isidentifier() and first != "__pycache__":
            imports.add(first)
    return tuple(sorted(imports))


def _wheel_scripts(archive: zipfile.ZipFile, members: Sequence[str]) -> tuple[str, ...]:
    entry_points = [
        name for name in members if name.endswith(".dist-info/entry_points.txt")
    ]
    if len(entry_points) > 1:
        raise PythonSupportVerificationError(
            "wheel contains more than one entry_points.txt"
        )
    if not entry_points:
        return ()
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(archive.read(entry_points[0]).decode("utf-8"))
    if not parser.has_section("console_scripts"):
        return ()
    return tuple(sorted(parser.options("console_scripts")))


def inspect_wheels(
    wheel_dir: Path, expected_distributions: Sequence[str]
) -> tuple[WheelRecord, ...]:
    """Validate and inventory one exact wheel for every expected distribution."""
    wheels = sorted(wheel_dir.glob("*.whl"))
    records: list[WheelRecord] = []
    for wheel in wheels:
        if not wheel.is_file() or wheel.is_symlink():
            raise PythonSupportVerificationError(
                f"wheel input must be a regular file: {wheel}"
            )
        try:
            with zipfile.ZipFile(wheel) as archive:
                members = _safe_wheel_members(archive, wheel)
                name, version, requires_python = _wheel_metadata(
                    archive, members, wheel
                )
                imports = _wheel_imports(members)
                scripts = _wheel_scripts(archive, members)
        except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise PythonSupportVerificationError(
                f"cannot inspect wheel {wheel}: {exc}"
            ) from exc
        records.append(
            WheelRecord(
                path=wheel.resolve(),
                distribution_name=name,
                version=version,
                requires_python=requires_python,
                import_names=imports,
                console_scripts=scripts,
                sha256=_sha256(wheel),
                byte_length=wheel.stat().st_size,
            )
        )

    expected = {canonicalize_name(name) for name in expected_distributions}
    actual = [canonicalize_name(record.distribution_name) for record in records]
    duplicates = sorted(name for name in set(actual) if actual.count(name) > 1)
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    if duplicates or missing or unexpected:
        raise PythonSupportVerificationError(
            "wheel inventory mismatch: "
            f"duplicates={duplicates}, missing={missing}, unexpected={unexpected}"
        )
    versions = {record.version for record in records}
    if len(versions) != 1:
        raise PythonSupportVerificationError(
            f"workspace wheel versions disagree: {sorted(versions)}"
        )
    return tuple(
        sorted(records, key=lambda record: canonicalize_name(record.distribution_name))
    )


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise PythonSupportVerificationError(
            "support-matrix commands require an absolute executable"
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


def _python_executable(environment_root: Path) -> Path:
    if os.name == "nt":
        return environment_root / "Scripts" / "python.exe"
    return environment_root / "bin" / "python"


def _inspector(records: Sequence[WheelRecord]) -> str:
    distributions = {record.distribution_name: record.version for record in records}
    imports = sorted({name for record in records for name in record.import_names})
    scripts = sorted({name for record in records for name in record.console_scripts})
    return "\n".join(
        [
            "import importlib",
            "import importlib.metadata as metadata",
            "import json",
            "from pathlib import Path",
            "import sysconfig",
            f"expected_distributions = {distributions!r}",
            f"import_names = {imports!r}",
            f"script_names = {scripts!r}",
            "purelib = Path(sysconfig.get_paths()['purelib']).resolve()",
            "versions = {name: metadata.version(name) for name in expected_distributions}",
            "assert versions == expected_distributions, (versions, expected_distributions)",
            "module_paths = {}",
            "for name in import_names:",
            "    module = importlib.import_module(name)",
            "    path = Path(module.__file__).resolve()",
            "    assert path.is_relative_to(purelib), (name, path, purelib)",
            "    module_paths[name] = str(path)",
            "entry_points = {entry.name: entry for entry in metadata.entry_points(group='console_scripts')}",
            "for name in script_names:",
            "    assert name in entry_points, name",
            "    assert callable(entry_points[name].load()), name",
            "print(json.dumps({'versions': versions, 'module_paths': module_paths, 'console_scripts': script_names}, sort_keys=True))",
        ]
    )


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _ensure_artifact_path(path: Path, repo_root: Path, *, label: str) -> Path:
    resolved = path.resolve()
    artifact_root = (repo_root / "artifacts").resolve()
    try:
        resolved.relative_to(artifact_root)
    except ValueError as exc:
        raise PythonSupportVerificationError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def run_python_support_matrix(
    *,
    repo_root: Path,
    wheel_dir: Path,
    output_path: Path,
    environment_root: Path,
    source_commit: str,
    uv_executable: Path,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Install and inspect the exact wheel set on all advertised interpreters."""
    repo_root = repo_root.resolve()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise PythonSupportVerificationError(
            "source commit must be a lowercase full Git SHA"
        )
    wheel_dir = _ensure_artifact_path(wheel_dir, repo_root, label="wheel directory")
    output_path = _ensure_artifact_path(output_path, repo_root, label="output path")
    environment_root = _ensure_artifact_path(
        environment_root, repo_root, label="environment root"
    )
    support = inspect_workspace(repo_root)
    records = inspect_wheels(wheel_dir, support.distribution_names)
    inspector = _inspector(records)
    environment_root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cache_root = output_path.parent / "cache"
    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(cache_root / "pycache"),
            "UV_CACHE_DIR": str(cache_root / "uv"),
        }
    )

    results: list[dict[str, object]] = []
    all_passed = True
    for python_version in support.python_versions:
        version_root = environment_root / f"python-{python_version}"
        python = _python_executable(version_root)
        commands = [
            [
                str(uv_executable.resolve()),
                "venv",
                str(version_root),
                "--python",
                python_version,
                "--clear",
            ],
            [
                str(uv_executable.resolve()),
                "pip",
                "install",
                "--python",
                str(python),
                *[str(record.path) for record in records],
            ],
            [
                str(uv_executable.resolve()),
                "pip",
                "check",
                "--python",
                str(python),
            ],
            [str(python), "-I", "-c", inspector],
        ]
        outcomes: list[CommandResult] = []
        for command in commands:
            outcome = runner(command, environment_root, environment)
            outcomes.append(outcome)
            if outcome.exit_code != 0:
                all_passed = False
                break
        results.append(
            {
                "python": python_version,
                "status": "passed"
                if len(outcomes) == len(commands) and outcomes[-1].exit_code == 0
                else "failed",
                "commands": [_command_payload(outcome) for outcome in outcomes],
            }
        )

    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.python_support_matrix.v1",
        "source_commit": source_commit,
        "created_at": datetime.now(UTC).isoformat(),
        "result": "passed" if all_passed else "failed",
        "environment": {
            "platform": platform.platform(),
            "runner_python": platform.python_version(),
        },
        "advertised_python_versions": list(support.python_versions),
        "distribution_count": len(records),
        "import_count": len(
            {name for record in records for name in record.import_names}
        ),
        "console_script_count": len(
            {name for record in records for name in record.console_scripts}
        ),
        "pyproject_identities": {
            path.resolve().relative_to(repo_root).as_posix(): _sha256(path)
            for path in support.pyproject_paths
        },
        "lock_identity": _sha256(repo_root / "uv.lock"),
        "wheels": [
            {
                "distribution_name": record.distribution_name,
                "version": record.version,
                "requires_python": record.requires_python,
                "filename": record.path.name,
                "sha256": record.sha256,
                "byte_length": record.byte_length,
                "import_names": list(record.import_names),
                "console_scripts": list(record.console_scripts),
            }
            for record in records
        ],
        "package_python_combinations": [
            {
                "combination_id": (
                    f"{distribution_name}--py{python_version.replace('.', '')}"
                ),
                "distribution_name": distribution_name,
                "package_class": package_class,
                "platform_promise": "os-independent",
                "python_version": python_version,
                "status": next(
                    row["status"] for row in results if row["python"] == python_version
                ),
            }
            for distribution_name, package_class in support.package_classes
            for python_version in support.python_versions
        ],
        "version_results": results,
        "limitations": [
            "platform coverage beyond the local runner remains owned by remote CI",
        ],
    }
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not all_passed:
        raise PythonSupportVerificationError(
            f"one or more Python support rows failed; inspect {output_path}"
        )
    return evidence


def _git_identity(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise PythonSupportVerificationError("git executable not found")
    status = subprocess.run(
        [git, "status", "--porcelain=v1"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise PythonSupportVerificationError(
            status.stderr.strip() or "git status failed"
        )
    if status.stdout.strip():
        raise PythonSupportVerificationError(
            "support matrix requires a clean source checkout"
        )
    identity = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise PythonSupportVerificationError(
            identity.stderr.strip() or "git rev-parse failed"
        )
    return identity.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install the complete workspace wheel set on every Python version "
            "advertised by package metadata."
        )
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--uv", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed Python support verifier."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    uv = args.uv or (Path(value) if (value := shutil.which("uv")) else None)
    if uv is None:
        raise SystemExit("uv executable not found; provide --uv")
    try:
        run_python_support_matrix(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            output_path=args.output,
            environment_root=args.environment_root,
            source_commit=_git_identity(repo_root),
            uv_executable=uv,
        )
    except PythonSupportVerificationError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
