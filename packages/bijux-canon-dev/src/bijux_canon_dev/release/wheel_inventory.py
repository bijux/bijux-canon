"""Validate wheel metadata, contents, integrity, and repository ownership."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
import configparser
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from email.parser import BytesParser
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import tomllib
from typing import Any, cast
import zipfile

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import (
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)


class WheelInventoryError(RuntimeError):
    """The wheel family does not match its source or release contract."""


@dataclass(frozen=True)
class PackagePolicy:
    """Source-owned expectations for one repository distribution."""

    package_key: str | None
    package_class: str
    pyproject_path: Path
    distribution_name: str
    requires_python: str
    dependencies: tuple[str, ...]
    dynamic_dependency_names: tuple[str, ...]
    optional_dependencies: tuple[tuple[str, tuple[str, ...]], ...]
    scripts: tuple[tuple[str, str], ...]
    license_text: str | None
    required_asset_patterns: tuple[str, ...]


@dataclass(frozen=True)
class CommandResult:
    """One external validation command and its captured result."""

    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], CommandResult]

_LEGAL_FILES = ("LICENSE", "NOTICE")
_SCHEMA_SUFFIXES = (".json", ".schema", ".yaml", ".yml", ".hash")


class _CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_pyproject(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise WheelInventoryError(f"cannot read {path}: {exc}") from exc


def _mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WheelInventoryError(f"{field} must be a table")
    return cast(dict[str, Any], value)


def _string_list(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WheelInventoryError(f"{field} must be a string list")
    return tuple(cast(list[str], value))


def _wheel_build(data: Mapping[str, Any]) -> dict[str, Any]:
    tool = _mapping(data.get("tool", {}), field="tool")
    hatch = _mapping(tool.get("hatch", {}), field="tool.hatch")
    build = _mapping(hatch.get("build", {}), field="tool.hatch.build")
    targets = _mapping(build.get("targets", {}), field="tool.hatch.build.targets")
    return _mapping(targets.get("wheel", {}), field="tool.hatch.build.targets.wheel")


def _runtime_asset_patterns(data: Mapping[str, Any]) -> tuple[str, ...]:
    wheel = _wheel_build(data)
    package_paths = _string_list(
        wheel.get("packages", []), field="tool.hatch.build.targets.wheel.packages"
    )
    patterns: set[str] = set()
    roots: dict[str, str] = {}
    for package_path in package_paths:
        pure = PurePosixPath(package_path)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise WheelInventoryError(f"unsafe wheel package path: {package_path}")
        root = pure.name
        roots[root] = package_path
        patterns.add(f"{root}/__init__.py")

    package_data = _mapping(
        wheel.get("package-data", {}),
        field="tool.hatch.build.targets.wheel.package-data",
    )
    for package_name, values in package_data.items():
        if package_name not in roots:
            raise WheelInventoryError(
                f"wheel package-data names undeclared package {package_name}"
            )
        for value in _string_list(values, field=f"wheel.package-data.{package_name}"):
            pure = PurePosixPath(value)
            if pure.is_absolute() or ".." in pure.parts:
                raise WheelInventoryError(f"unsafe wheel package-data path: {value}")
            patterns.add(f"{package_name}/{value}")

    for value in _string_list(wheel.get("include", []), field="wheel.include"):
        pure = PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts:
            raise WheelInventoryError(f"unsafe wheel include path: {value}")
        parts = pure.parts
        if len(parts) >= 2 and parts[0] == "src" and parts[1] in roots:
            patterns.add(PurePosixPath(*parts[1:]).as_posix())
    return tuple(sorted(patterns))


def _package_policy(
    *,
    package_key: str | None,
    package_class: str,
    pyproject_path: Path,
) -> PackagePolicy:
    data = _load_pyproject(pyproject_path)
    project = _mapping(data.get("project"), field=f"project in {pyproject_path}")
    name = project.get("name")
    requires_python = project.get("requires-python")
    if not isinstance(name, str) or not name:
        raise WheelInventoryError(f"project name is missing in {pyproject_path}")
    if not isinstance(requires_python, str) or not requires_python:
        raise WheelInventoryError(
            f"project requires-python is missing in {pyproject_path}"
        )
    dependencies = _string_list(project.get("dependencies", []), field="dependencies")
    dynamic = set(_string_list(project.get("dynamic", []), field="project.dynamic"))
    dynamic_dependency_names: tuple[str, ...] = ()
    if "dependencies" in dynamic:
        tool = _mapping(data.get("tool", {}), field="tool")
        hatch = _mapping(tool.get("hatch", {}), field="tool.hatch")
        metadata = _mapping(hatch.get("metadata", {}), field="tool.hatch.metadata")
        hooks = _mapping(metadata.get("hooks", {}), field="tool.hatch.metadata.hooks")
        custom = _mapping(
            hooks.get("custom", {}), field="tool.hatch.metadata.hooks.custom"
        )
        canonical_name = custom.get("canonical-name")
        same_version = custom.get("same-version-dependencies")
        external = custom.get("external-dependencies", [])
        if canonical_name is not None:
            if not isinstance(canonical_name, str) or not canonical_name:
                raise WheelInventoryError(
                    "dynamic canonical-name must identify one distribution"
                )
            if same_version is not None or external:
                raise WheelInventoryError(
                    "dynamic dependency hook modes cannot be combined"
                )
            dynamic_dependency_names = (canonical_name,)
        else:
            dynamic_dependency_names = _string_list(
                same_version,
                field="tool.hatch.metadata.hooks.custom.same-version-dependencies",
            )
            dependencies = _string_list(
                external,
                field="tool.hatch.metadata.hooks.custom.external-dependencies",
            )
            if not dynamic_dependency_names:
                raise WheelInventoryError(
                    "dynamic dependencies require same-version dependencies"
                )
    optional_raw = _mapping(
        project.get("optional-dependencies", {}), field="optional-dependencies"
    )
    optional_dependencies = tuple(
        sorted(
            (
                canonicalize_name(extra),
                _string_list(values, field=f"optional-dependencies.{extra}"),
            )
            for extra, values in optional_raw.items()
        )
    )
    scripts_raw = _mapping(project.get("scripts", {}), field="project.scripts")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in scripts_raw.items()
    ):
        raise WheelInventoryError("project.scripts must map strings to strings")
    license_value = project.get("license")
    license_text: str | None = None
    if license_value is not None:
        license_table = _mapping(license_value, field="project.license")
        value = license_table.get("text")
        if not isinstance(value, str) or not value:
            raise WheelInventoryError("project.license.text must be a string")
        license_text = value
    return PackagePolicy(
        package_key=package_key,
        package_class=package_class,
        pyproject_path=pyproject_path,
        distribution_name=name,
        requires_python=requires_python,
        dependencies=dependencies,
        dynamic_dependency_names=dynamic_dependency_names,
        optional_dependencies=optional_dependencies,
        scripts=tuple(sorted(cast(dict[str, str], scripts_raw).items())),
        license_text=license_text,
        required_asset_patterns=(
            _runtime_asset_patterns(data) if package_key is not None else ()
        ),
    )


def inspect_workspace_policy(repo_root: Path) -> tuple[PackagePolicy, ...]:
    """Read the exact package family and wheel expectations from source metadata."""
    repo_root = repo_root.resolve()
    root_path = repo_root / "pyproject.toml"
    root_data = _load_pyproject(root_path)
    tool = _mapping(root_data.get("tool", {}), field="tool")
    workspace = _mapping(tool.get("bijux_canon"), field="tool.bijux_canon")
    package_dirs = _mapping(
        workspace.get("package_dirs"), field="tool.bijux_canon.package_dirs"
    )
    if not package_dirs or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in package_dirs.items()
    ):
        raise WheelInventoryError("package_dirs must map package keys to paths")
    primary = set(
        _string_list(workspace.get("primary_packages"), field="primary_packages")
    )
    compatibility = set(
        _string_list(workspace.get("compat_packages"), field="compat_packages")
    )
    if primary & compatibility or primary | compatibility != set(package_dirs):
        raise WheelInventoryError(
            "primary and compatibility inventories must partition package_dirs"
        )

    policies: list[PackagePolicy] = []
    for package_key, relative in sorted(cast(dict[str, str], package_dirs).items()):
        path = (repo_root / relative / "pyproject.toml").resolve()
        try:
            path.relative_to(repo_root)
        except ValueError as exc:
            raise WheelInventoryError(
                f"package pyproject escapes repository: {relative}"
            ) from exc
        policies.append(
            _package_policy(
                package_key=package_key,
                package_class=(
                    "canonical" if package_key in primary else "compatibility"
                ),
                pyproject_path=path,
            )
        )
    normalized = [canonicalize_name(policy.distribution_name) for policy in policies]
    if len(normalized) != len(set(normalized)):
        raise WheelInventoryError("workspace distribution names are not unique")
    script_owners: dict[str, dict[str, list[str]]] = {}
    for policy in policies:
        for script, entrypoint in policy.scripts:
            targets = script_owners.setdefault(script, {})
            targets.setdefault(entrypoint, []).append(policy.distribution_name)
    conflicting_scripts = {
        script: targets
        for script, targets in script_owners.items()
        if len(targets) > 1
    }
    if conflicting_scripts:
        detail_rows: list[str] = []
        for script, targets in sorted(conflicting_scripts.items()):
            target_rows = [
                f"{target}: {', '.join(sorted(owners))}"
                for target, owners in sorted(targets.items())
            ]
            detail_rows.append(f"{script} ({'; '.join(target_rows)})")
        details = ", ".join(detail_rows)
        raise WheelInventoryError(
            f"workspace console scripts require one deterministic entrypoint: {details}"
        )
    return tuple(
        sorted(policies, key=lambda item: canonicalize_name(item.distribution_name))
    )


def _safe_members(archive: zipfile.ZipFile, wheel: Path) -> tuple[str, ...]:
    members: list[str] = []
    for info in archive.infolist():
        name = info.filename
        pure = PurePosixPath(name)
        if (
            not name
            or pure.is_absolute()
            or ".." in pure.parts
            or "\\" in name
            or stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK
        ):
            raise WheelInventoryError(f"unsafe member in {wheel.name}: {name}")
        members.append(name)
    duplicates = sorted(name for name, count in Counter(members).items() if count > 1)
    if duplicates:
        raise WheelInventoryError(
            f"duplicate archive members in {wheel.name}: {duplicates}"
        )
    return tuple(members)


def _one_member(members: Sequence[str], suffix: str, wheel: Path) -> str:
    matches = [name for name in members if name.endswith(suffix)]
    if len(matches) != 1:
        raise WheelInventoryError(
            f"{wheel.name} must contain exactly one {suffix}: {matches}"
        )
    return matches[0]


def _requirement_identity(value: str) -> tuple[object, ...]:
    requirement = Requirement(value)
    return (
        canonicalize_name(requirement.name),
        tuple(sorted(canonicalize_name(extra) for extra in requirement.extras)),
        str(requirement.specifier),
        requirement.url or "",
        str(requirement.marker) if requirement.marker else "",
    )


def _expected_requirements(
    policy: PackagePolicy, *, version: str
) -> Counter[tuple[object, ...]]:
    values = list(policy.dependencies)
    values.extend(f"{name}=={version}" for name in policy.dynamic_dependency_names)
    for extra, requirements in policy.optional_dependencies:
        for value in requirements:
            parsed = Requirement(value)
            base = value.split(";", maxsplit=1)[0].strip()
            marker = str(parsed.marker) if parsed.marker else ""
            combined = (
                f"({marker}) and extra == '{extra}'"
                if marker
                else f"extra == '{extra}'"
            )
            values.append(f"{base}; {combined}")
    return Counter(_requirement_identity(value) for value in values)


def _entry_points(
    archive: zipfile.ZipFile, members: Sequence[str], wheel: Path
) -> dict[str, str]:
    matches = [name for name in members if name.endswith(".dist-info/entry_points.txt")]
    if len(matches) > 1:
        raise WheelInventoryError(
            f"{wheel.name} contains multiple entry_points.txt files"
        )
    if not matches:
        return {}
    parser = _CaseSensitiveConfigParser(interpolation=None)
    parser.read_string(archive.read(matches[0]).decode("utf-8"))
    if not parser.has_section("console_scripts"):
        return {}
    return dict(sorted(parser.items("console_scripts")))


def _validate_record(
    archive: zipfile.ZipFile,
    members: Sequence[str],
    record_name: str,
) -> list[str]:
    issues: list[str] = []
    try:
        rows = list(csv.reader(io.StringIO(archive.read(record_name).decode("utf-8"))))
    except (UnicodeDecodeError, csv.Error) as exc:
        return [f"invalid-record:{exc}"]
    if any(len(row) != 3 for row in rows):
        return ["invalid-record-columns"]
    paths = [row[0] for row in rows]
    if Counter(paths) != Counter(members):
        issues.append("record-members")
    for path, digest, size in rows:
        if path == record_name:
            if digest or size:
                issues.append("record-self-entry")
            continue
        if path not in members:
            continue
        payload = archive.read(path)
        expected_digest = (
            base64.urlsafe_b64encode(hashlib.sha256(payload).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        if digest != f"sha256={expected_digest}":
            issues.append(f"record-hash:{path}")
        if size != str(len(payload)):
            issues.append(f"record-size:{path}")
    return issues


def _source_leaks(
    archive: zipfile.ZipFile,
    members: Sequence[str],
    repo_root: Path,
) -> list[str]:
    leaks = [
        name
        for name in members
        if (
            "/tests/" in f"/{name}"
            or "/artifacts/" in f"/{name}"
            or "__pycache__" in PurePosixPath(name).parts
            or name.endswith((".pyc", ".pyo"))
            or name.startswith((".git/", "packages/", "src/"))
        )
    ]
    source_path = repo_root.as_posix().encode("utf-8")
    for name in members:
        info = archive.getinfo(name)
        if info.file_size > 2 * 1024 * 1024:
            continue
        if name.endswith((".py", ".md", ".txt", "/METADATA", "/WHEEL")):
            if source_path in archive.read(name):
                leaks.append(f"embedded-source-path:{name}")
    return sorted(leaks)


def _metadata_message(archive: zipfile.ZipFile, name: str) -> Message:
    return BytesParser().parsebytes(archive.read(name))


def _inspect_wheel(
    *, wheel: Path, policy: PackagePolicy, repo_root: Path
) -> dict[str, object]:
    issues: list[str] = []
    parsed_name, parsed_version, _build, filename_tags = parse_wheel_filename(
        wheel.name
    )
    with zipfile.ZipFile(wheel) as archive:
        members = _safe_members(archive, wheel)
        metadata_name = _one_member(members, ".dist-info/METADATA", wheel)
        wheel_name = _one_member(members, ".dist-info/WHEEL", wheel)
        record_name = _one_member(members, ".dist-info/RECORD", wheel)
        metadata = _metadata_message(archive, metadata_name)
        actual_name = metadata.get("Name")
        actual_version = metadata.get("Version")
        actual_requires_python = metadata.get("Requires-Python")
        if not actual_name or canonicalize_name(actual_name) != canonicalize_name(
            policy.distribution_name
        ):
            issues.append("metadata-name")
        if canonicalize_name(str(parsed_name)) != canonicalize_name(
            policy.distribution_name
        ):
            issues.append("filename-name")
        if not actual_version or actual_version != str(parsed_version):
            issues.append("metadata-version")
        try:
            if not actual_requires_python or SpecifierSet(
                actual_requires_python
            ) != SpecifierSet(policy.requires_python):
                issues.append("requires-python")
        except InvalidSpecifier:
            issues.append("requires-python")

        actual_requirements = metadata.get_all("Requires-Dist") or []
        try:
            if Counter(
                _requirement_identity(value) for value in actual_requirements
            ) != _expected_requirements(policy, version=str(parsed_version)):
                issues.append("dependencies")
        except InvalidRequirement:
            issues.append("dependencies")
        actual_extras = sorted(
            canonicalize_name(value)
            for value in (metadata.get_all("Provides-Extra") or [])
        )
        expected_extras = sorted(
            extra for extra, _values in policy.optional_dependencies
        )
        if actual_extras != expected_extras:
            issues.append("extras")

        actual_license = metadata.get("License-Expression") or metadata.get("License")
        if actual_license != policy.license_text:
            issues.append("license-expression")
        license_headers = set(metadata.get_all("License-File") or [])
        missing_legal_files: list[str] = []
        for legal_name in _LEGAL_FILES:
            candidates = [
                name
                for name in members
                if name.endswith(f".dist-info/licenses/{legal_name}")
            ]
            source = repo_root / legal_name
            if (
                legal_name not in license_headers
                or len(candidates) != 1
                or not source.is_file()
                or archive.read(candidates[0]) != source.read_bytes()
            ):
                missing_legal_files.append(legal_name)
        if missing_legal_files:
            issues.append("legal-files")

        scripts = _entry_points(archive, members, wheel)
        if scripts != dict(policy.scripts):
            issues.append("entry-points")
        missing_assets = [
            pattern
            for pattern in policy.required_asset_patterns
            if not any(fnmatch.fnmatchcase(name, pattern) for name in members)
        ]
        if missing_assets:
            issues.append("runtime-assets")
        leaks = _source_leaks(archive, members, repo_root)
        if leaks:
            issues.append("source-leaks")

        wheel_metadata = _metadata_message(archive, wheel_name)
        actual_tags = set(wheel_metadata.get_all("Tag") or [])
        expected_tags = {str(tag) for tag in filename_tags}
        if actual_tags != expected_tags:
            issues.append("wheel-tags")
        issues.extend(_validate_record(archive, members, record_name))
        schema_assets = sorted(
            name for name in members if name.endswith(_SCHEMA_SUFFIXES)
        )

    return {
        "package_key": policy.package_key,
        "package_id": policy.distribution_name,
        "package_class": policy.package_class,
        "wheel": wheel.name,
        "wheel_sha256": _sha256(wheel),
        "wheel_bytes": wheel.stat().st_size,
        "version": str(parsed_version),
        "requires_python": actual_requires_python,
        "dependencies": actual_requirements,
        "extras": actual_extras,
        "license": actual_license,
        "entry_points": scripts,
        "tags": sorted(actual_tags),
        "file_count": len(members),
        "files": sorted(members),
        "schema_assets": schema_assets,
        "required_runtime_assets": list(policy.required_asset_patterns),
        "missing_runtime_assets": missing_assets,
        "missing_legal_files": missing_legal_files,
        "source_leaks": leaks,
        "issues": sorted(set(issues)),
        "status": "passed" if not issues else "failed",
    }


def _default_runner(
    command: Sequence[str], cwd: Path, environment: Mapping[str, str]
) -> CommandResult:
    if not command or not Path(command[0]).is_absolute():
        raise WheelInventoryError("external commands require an absolute executable")
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
        raise WheelInventoryError(
            f"{label} must be under the repository artifacts directory: {path}"
        ) from exc
    return resolved


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise WheelInventoryError(f"path escapes repository: {path}") from exc


def _command_payload(result: CommandResult) -> dict[str, object]:
    return {
        "command": list(result.command),
        "duration_seconds": result.duration_seconds,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _inspect_sdist(
    *, sdist: Path, policy: PackagePolicy, version: str
) -> dict[str, object]:
    """Inspect one source archive without extracting it."""
    issues: list[str] = []
    try:
        parsed_name, parsed_version = parse_sdist_filename(sdist.name)
    except ValueError as exc:
        raise WheelInventoryError(f"invalid sdist filename: {sdist.name}") from exc
    if canonicalize_name(str(parsed_name)) != canonicalize_name(
        policy.distribution_name
    ):
        issues.append("distribution-name")
    if str(parsed_version) != version:
        issues.append("version")

    with tarfile.open(sdist, mode="r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            issues.append("duplicate-members")
        unsafe = []
        for member in members:
            pure = PurePosixPath(member.name)
            if (
                not member.name
                or pure.is_absolute()
                or ".." in pure.parts
                or "\\" in member.name
                or member.issym()
                or member.islnk()
                or member.isdev()
            ):
                unsafe.append(member.name)
        if unsafe:
            issues.append("unsafe-members")
        roots = {PurePosixPath(name).parts[0] for name in names if name}
        if roots != {sdist.name.removesuffix(".tar.gz")}:
            issues.append("archive-root")
        pkg_info = [member for member in members if member.name.endswith("/PKG-INFO")]
        pyprojects = [
            member for member in members if member.name.endswith("/pyproject.toml")
        ]
        if len(pkg_info) != 1:
            issues.append("pkg-info")
        else:
            extracted = archive.extractfile(pkg_info[0])
            if extracted is None:
                issues.append("pkg-info")
            else:
                metadata = BytesParser().parsebytes(extracted.read())
                if canonicalize_name(metadata.get("Name", "")) != canonicalize_name(
                    policy.distribution_name
                ):
                    issues.append("pkg-info-name")
                if metadata.get("Version") != version:
                    issues.append("pkg-info-version")
        if len(pyprojects) != 1:
            issues.append("pyproject")

    return {
        "package_id": policy.distribution_name,
        "package_class": policy.package_class,
        "sdist": sdist.name,
        "sdist_sha256": _sha256(sdist),
        "sdist_bytes": sdist.stat().st_size,
        "version": str(parsed_version),
        "member_count": len(names),
        "issues": sorted(set(issues)),
        "status": "passed" if not issues else "failed",
    }


def run_wheel_inventory(
    *,
    repo_root: Path,
    wheel_dir: Path,
    output_path: Path,
    source_commit: str,
    twine_python: Path,
    runner: CommandRunner = _default_runner,
) -> dict[str, object]:
    """Validate an exact wheel family and retain a hash-bound inventory."""
    repo_root = repo_root.resolve()
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise WheelInventoryError("source commit must be a lowercase full Git SHA")
    wheel_dir = _artifact_path(wheel_dir, repo_root, label="wheel directory")
    output_path = _artifact_path(output_path, repo_root, label="output path")
    twine_python = twine_python.absolute()
    if not twine_python.is_absolute():
        raise WheelInventoryError("Twine Python executable must be absolute")
    policies = inspect_workspace_policy(repo_root)
    expected = {
        canonicalize_name(policy.distribution_name): policy for policy in policies
    }

    wheel_map: dict[str, list[Path]] = {}
    sdist_map: dict[str, list[Path]] = {}
    inventory_failures: list[str] = []
    for wheel in sorted(wheel_dir.glob("*.whl")):
        if not wheel.is_file() or wheel.is_symlink():
            inventory_failures.append(f"invalid-wheel-input:{wheel.name}")
            continue
        try:
            name, _version, _build, _tags = parse_wheel_filename(wheel.name)
        except ValueError:
            inventory_failures.append(f"invalid-wheel-filename:{wheel.name}")
            continue
        wheel_map.setdefault(canonicalize_name(str(name)), []).append(wheel)
    for sdist in sorted(wheel_dir.glob("*.tar.gz")):
        if not sdist.is_file() or sdist.is_symlink():
            inventory_failures.append(f"invalid-sdist-input:{sdist.name}")
            continue
        try:
            name, _version = parse_sdist_filename(sdist.name)
        except ValueError:
            inventory_failures.append(f"invalid-sdist-filename:{sdist.name}")
            continue
        sdist_map.setdefault(canonicalize_name(str(name)), []).append(sdist)
    missing = sorted(set(expected) - set(wheel_map))
    unexpected = sorted(set(wheel_map) - set(expected))
    duplicates = sorted(name for name, values in wheel_map.items() if len(values) > 1)
    inventory_failures.extend(f"missing-wheel:{name}" for name in missing)
    inventory_failures.extend(f"unexpected-wheel:{name}" for name in unexpected)
    inventory_failures.extend(f"duplicate-wheel:{name}" for name in duplicates)
    missing_sdists = sorted(set(expected) - set(sdist_map))
    unexpected_sdists = sorted(set(sdist_map) - set(expected))
    duplicate_sdists = sorted(
        name for name, values in sdist_map.items() if len(values) > 1
    )
    inventory_failures.extend(f"missing-sdist:{name}" for name in missing_sdists)
    inventory_failures.extend(f"unexpected-sdist:{name}" for name in unexpected_sdists)
    inventory_failures.extend(f"duplicate-sdist:{name}" for name in duplicate_sdists)

    records: list[dict[str, object]] = []
    for name, policy in sorted(expected.items()):
        wheels = wheel_map.get(name, [])
        if len(wheels) != 1:
            continue
        try:
            records.append(
                _inspect_wheel(wheel=wheels[0], policy=policy, repo_root=repo_root)
            )
        except (
            OSError,
            UnicodeDecodeError,
            ValueError,
            zipfile.BadZipFile,
            WheelInventoryError,
        ) as exc:
            records.append(
                {
                    "package_key": policy.package_key,
                    "package_id": policy.distribution_name,
                    "package_class": policy.package_class,
                    "wheel": wheels[0].name,
                    "issues": [f"inspection-error:{exc}"],
                    "status": "failed",
                }
            )

    versions = sorted(
        {
            cast(str, record["version"])
            for record in records
            if isinstance(record.get("version"), str)
        }
    )
    if len(versions) != 1:
        inventory_failures.append(f"mixed-wheel-versions:{versions}")

    sdist_records: list[dict[str, object]] = []
    candidate_version = versions[0] if len(versions) == 1 else ""
    for name, policy in sorted(expected.items()):
        sdists = sdist_map.get(name, [])
        if len(sdists) != 1:
            continue
        try:
            sdist_records.append(
                _inspect_sdist(
                    sdist=sdists[0], policy=policy, version=candidate_version
                )
            )
        except (OSError, tarfile.TarError, WheelInventoryError) as exc:
            sdist_records.append(
                {
                    "package_id": policy.distribution_name,
                    "package_class": policy.package_class,
                    "sdist": sdists[0].name,
                    "issues": [f"inspection-error:{exc}"],
                    "status": "failed",
                }
            )

    twine_artifacts = sorted(
        [path for values in wheel_map.values() for path in values]
        + [path for values in sdist_map.values() for path in values]
    )
    environment = dict(os.environ)
    cache_root = output_path.parent / "cache"
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(cache_root / "pycache"),
            "XDG_CACHE_HOME": str(cache_root / "xdg"),
        }
    )
    twine_result = runner(
        [
            str(twine_python),
            "-m",
            "twine",
            "check",
            *[str(path.resolve()) for path in twine_artifacts],
        ],
        repo_root,
        environment,
    )
    if twine_result.exit_code != 0:
        inventory_failures.append("twine-check")
    for record in records:
        if record["status"] == "failed":
            inventory_failures.append(
                f"wheel-contract:{record['package_id']}:{','.join(cast(list[str], record['issues']))}"
            )
    for record in sdist_records:
        if record["status"] == "failed":
            inventory_failures.append(
                f"sdist-contract:{record['package_id']}:{','.join(cast(list[str], record['issues']))}"
            )

    package_results = [
        {
            "package_id": record["package_id"],
            "package_class": record["package_class"],
            "status": record["status"],
        }
        for record in records
        if record.get("package_key") is not None
    ]
    evidence: dict[str, object] = {
        "schema_version": "bijux.canon.wheel_inventory.v1",
        "source_commit": source_commit,
        "created_at": datetime.now(UTC).isoformat(),
        "result": "passed" if not inventory_failures else "failed",
        "environment": {
            "platform": platform.platform(),
            "runner_python": platform.python_version(),
        },
        "wheel_directory": _relative(wheel_dir, repo_root),
        "wheel_count": sum(len(values) for values in wheel_map.values()),
        "sdist_count": sum(len(values) for values in sdist_map.values()),
        "artifact_count": len(twine_artifacts),
        "package_count": len(package_results),
        "version": versions[0] if len(versions) == 1 else None,
        "pyproject_identities": {
            _relative(policy.pyproject_path, repo_root): _sha256(policy.pyproject_path)
            for policy in policies
        },
        "lock_identity": _sha256(repo_root / "uv.lock"),
        "twine": _command_payload(twine_result),
        "records": records,
        "sdist_records": sdist_records,
        "package_results": package_results,
        "retained_failures": sorted(set(inventory_failures)),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if inventory_failures:
        raise WheelInventoryError(f"wheel inventory failed; inspect {output_path}")
    return evidence


def _git_identity(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise WheelInventoryError("git executable not found")
    status = subprocess.run(
        [git, "status", "--porcelain=v1"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise WheelInventoryError(status.stderr.strip() or "git status failed")
    if status.stdout.strip():
        raise WheelInventoryError("wheel inventory requires a clean source checkout")
    identity = subprocess.run(
        [git, "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise WheelInventoryError(identity.stderr.strip() or "git rev-parse failed")
    return identity.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the complete repository wheel family's metadata and contents."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--twine-python", type=Path, default=Path(sys.executable))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed wheel inventory command."""
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        run_wheel_inventory(
            repo_root=repo_root,
            wheel_dir=args.wheel_dir,
            output_path=args.output,
            source_commit=_git_identity(repo_root),
            twine_python=args.twine_python,
        )
    except WheelInventoryError as exc:
        raise SystemExit(str(exc)) from exc
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
