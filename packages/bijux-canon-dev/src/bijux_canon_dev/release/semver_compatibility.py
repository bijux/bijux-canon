"""Compare public release surfaces with the previous supported release."""

from __future__ import annotations

import argparse
import ast
from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tomllib
from typing import Any, cast

from packaging.version import InvalidVersion, Version
import yaml


class SemverCompatibilityError(RuntimeError):
    """A prior public surface was removed without an admitted migration."""


_HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}


def _require(condition: object, message: str) -> None:
    if not condition:
        raise SemverCompatibilityError(message)


def _object(value: object, message: str) -> dict[str, Any]:
    _require(isinstance(value, dict), message)
    return cast(dict[str, Any], value)


def _strings(value: object, message: str) -> list[str]:
    _require(
        isinstance(value, list) and all(isinstance(item, str) for item in value),
        message,
    )
    return cast(list[str], value)


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ("git", "-C", str(repository), *arguments),
        capture_output=True,
        check=False,
    )
    _require(
        completed.returncode == 0,
        f"git {' '.join(arguments)} failed: {completed.stderr.decode(errors='replace').strip()}",
    )
    return completed.stdout


def _revision_file(repository: Path, revision: str, path: str) -> bytes:
    return _git(repository, "show", f"{revision}:{path}")


def _root_initializers(repository: Path, revision: str) -> tuple[str, ...]:
    names = (
        _git(repository, "ls-tree", "-r", "--name-only", revision).decode().splitlines()
    )
    return tuple(
        path
        for path in names
        if path.startswith("packages/")
        and "/src/" in path
        and path.endswith("/__init__.py")
        and path.count("/") == 4
    )


def _assigned_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name) and not target.id.startswith("_"):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {name for item in target.elts for name in _assigned_names(item)}
    return set()


def _public_exports(payload: bytes, path: str) -> set[str]:
    tree = ast.parse(payload.decode("utf-8"), filename=path)
    explicit: set[str] | None = None
    visible: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                visible.add(node.name)
        elif isinstance(node, ast.Import):
            visible.update(
                alias.asname or alias.name.split(".")[0]
                for alias in node.names
                if not (alias.asname or alias.name).startswith("_")
            )
        elif isinstance(node, ast.ImportFrom):
            visible.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name != "*"
                and not (alias.asname or alias.name).startswith("_")
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        value = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
                    else:
                        if isinstance(value, (list, tuple)) and all(
                            isinstance(item, str) for item in value
                        ):
                            explicit = set(cast(Sequence[str], value))
                visible.update(_assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            visible.update(_assigned_names(node.target))
    return explicit if explicit is not None else visible


def _project_scripts(payload: bytes, path: str) -> dict[str, str]:
    document = tomllib.loads(payload.decode("utf-8"))
    project = _object(document.get("project"), f"project table is missing: {path}")
    scripts = _object(project.get("scripts", {}), f"scripts table is invalid: {path}")
    _require(
        all(
            isinstance(name, str) and isinstance(target, str)
            for name, target in scripts.items()
        ),
        f"script entry is invalid: {path}",
    )
    return cast(dict[str, str], scripts)


def _schema_surface(document: Mapping[str, Any]) -> set[str]:
    surface: set[str] = set()
    paths = _object(document.get("paths", {}), "OpenAPI paths are invalid")
    for route, raw_item in paths.items():
        item = _object(raw_item, f"OpenAPI path item is invalid: {route}")
        shared = item.get("parameters", [])
        _require(isinstance(shared, list), f"OpenAPI parameters are invalid: {route}")
        for method, raw_operation in item.items():
            if method not in _HTTP_METHODS:
                continue
            operation = _object(
                raw_operation, f"OpenAPI operation is invalid: {method} {route}"
            )
            identity = f"{method.upper()} {route}"
            surface.add(f"operation:{identity}")
            parameters = operation.get("parameters", [])
            _require(
                isinstance(parameters, list),
                f"operation parameters are invalid: {identity}",
            )
            for raw_parameter in [*shared, *parameters]:
                parameter = _object(
                    raw_parameter, f"OpenAPI parameter is invalid: {identity}"
                )
                if "$ref" in parameter:
                    surface.add(f"parameter:{identity}:ref:{parameter['$ref']}")
                elif parameter.get("required") is True:
                    surface.add(
                        f"parameter:{identity}:{parameter.get('in')}:{parameter.get('name')}:required"
                    )
            responses = _object(
                operation.get("responses", {}), f"responses are invalid: {identity}"
            )
            surface.update(f"response:{identity}:{code}" for code in responses)
    components = _object(
        document.get("components", {}), "OpenAPI components are invalid"
    )
    schemas = _object(components.get("schemas", {}), "OpenAPI schemas are invalid")
    for name, raw_schema in schemas.items():
        schema = _object(raw_schema, f"component schema is invalid: {name}")
        surface.add(f"schema:{name}")
        required = _strings(
            schema.get("required", []), f"required fields are invalid: {name}"
        )
        surface.update(f"required:{name}:{field}" for field in required)
    return surface


def _deprecation_records(policy: Mapping[str, Any]) -> list[dict[str, str]]:
    candidate = Version(str(policy.get("candidate_version")))
    raw_records = policy.get("deprecations")
    _require(
        isinstance(raw_records, list) and raw_records, "deprecation policy is missing"
    )
    records: list[dict[str, str]] = []
    for raw_record in cast(list[object], raw_records):
        record = _object(raw_record, "deprecation record is invalid")
        for field in (
            "alternative",
            "deprecated_since",
            "owner",
            "removal_not_before",
            "surface",
        ):
            _require(
                isinstance(record.get(field), str) and record[field],
                f"deprecation {field} is missing",
            )
        try:
            deprecated = Version(cast(str, record["deprecated_since"]))
            removal = Version(cast(str, record["removal_not_before"]))
        except InvalidVersion as exc:
            raise SemverCompatibilityError(
                "deprecation window has an invalid version"
            ) from exc
        _require(
            deprecated <= candidate < removal,
            f"deprecation window is closed: {record['surface']}",
        )
        records.append(cast(dict[str, str], record))
    _require(
        len({record["surface"] for record in records}) == len(records),
        "deprecation surfaces must be unique",
    )
    return records


def compare_release_surfaces(repository: Path, policy_path: Path) -> dict[str, Any]:
    """Build and validate the prior-to-candidate public compatibility diff."""
    repository = repository.resolve()
    policy_bytes = policy_path.read_bytes()
    policy = _object(json.loads(policy_bytes), "semver policy must be an object")
    _require(
        policy.get("schema_version") == "bijux.canon.semver_compatibility_policy.v1",
        "semver policy schema mismatch",
    )
    prior = str(policy.get("prior_release"))
    prior_commit = _git(repository, "rev-parse", f"{prior}^{{commit}}").decode().strip()
    source_commit = _git(repository, "rev-parse", "HEAD^{commit}").decode().strip()

    import_diffs: list[dict[str, Any]] = []
    for path in _root_initializers(repository, prior):
        current_path = repository / path
        _require(
            current_path.is_file(), f"prior public import root was removed: {path}"
        )
        previous_exports = _public_exports(
            _revision_file(repository, prior, path), path
        )
        current_exports = _public_exports(current_path.read_bytes(), path)
        removed = sorted(previous_exports - current_exports)
        _require(
            not removed, f"prior public imports were removed from {path}: {removed}"
        )
        import_diffs.append(
            {
                "added": sorted(current_exports - previous_exports),
                "path": path,
                "retained_count": len(previous_exports),
            }
        )

    command_diffs: list[dict[str, Any]] = []
    pyprojects = [
        path
        for path in _git(repository, "ls-tree", "-r", "--name-only", prior)
        .decode()
        .splitlines()
        if path.startswith("packages/")
        and path.endswith("/pyproject.toml")
        and path.count("/") == 2
    ]
    for path in pyprojects:
        current_path = repository / path
        _require(
            current_path.is_file(), f"prior distribution metadata was removed: {path}"
        )
        previous_scripts = _project_scripts(
            _revision_file(repository, prior, path), path
        )
        current_scripts = _project_scripts(current_path.read_bytes(), path)
        removed = sorted(set(previous_scripts) - set(current_scripts))
        _require(
            not removed, f"prior installed commands were removed from {path}: {removed}"
        )
        command_diffs.append(
            {
                "added": sorted(set(current_scripts) - set(previous_scripts)),
                "path": path,
                "retained": sorted(set(previous_scripts) & set(current_scripts)),
                "retargeted": sorted(
                    name
                    for name in set(previous_scripts) & set(current_scripts)
                    if previous_scripts[name] != current_scripts[name]
                ),
            }
        )

    schema_diffs: list[dict[str, Any]] = []
    schema_paths = [
        path
        for path in _git(repository, "ls-tree", "-r", "--name-only", prior)
        .decode()
        .splitlines()
        if path.startswith("apis/") and path.endswith("/v1/schema.yaml")
    ]
    for path in schema_paths:
        current_path = repository / path
        _require(current_path.is_file(), f"prior schema was removed: {path}")
        previous_document = _object(
            yaml.safe_load(_revision_file(repository, prior, path)),
            f"prior OpenAPI document is invalid: {path}",
        )
        current_document = _object(
            yaml.safe_load(current_path.read_bytes()),
            f"current OpenAPI document is invalid: {path}",
        )
        previous_schema = _schema_surface(previous_document)
        current_schema = _schema_surface(current_document)
        removed = sorted(previous_schema - current_schema)
        _require(
            not removed, f"prior schema surface was removed from {path}: {removed}"
        )
        schema_diffs.append(
            {
                "added": sorted(current_schema - previous_schema),
                "path": path,
                "retained_count": len(previous_schema),
            }
        )

    tests = _strings(
        policy.get("workspace_acceptance_tests"), "workspace tests are missing"
    )
    _require(tests, "workspace acceptance tests are empty")
    for test in tests:
        _require(
            (repository / test).is_file(),
            f"workspace acceptance test is missing: {test}",
        )
    rollback = policy.get("workspace_rollback_documentation")
    _require(
        isinstance(rollback, str) and (repository / rollback).is_file(),
        "rollback documentation is missing",
    )

    return {
        "candidate_version": policy["candidate_version"],
        "commands": command_diffs,
        "deprecations": _deprecation_records(policy),
        "imports": import_diffs,
        "policy_sha256": sha256(policy_bytes).hexdigest(),
        "prior_commit": prior_commit,
        "prior_release": prior,
        "result": "passed",
        "schemas": schema_diffs,
        "schema_version": "bijux.canon.semver_compatibility.v1",
        "source_commit": source_commit,
        "workspace_migration": {
            "acceptance_tests": tests,
            "rollback_documentation": rollback,
        },
    }


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--policy", type=Path, default=Path("configs/semver-compatibility.json")
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the compatibility diff and optionally retain canonical evidence."""
    arguments = _arguments(argv)
    repository = arguments.repo_root.resolve()
    policy = (
        arguments.policy
        if arguments.policy.is_absolute()
        else repository / arguments.policy
    )
    try:
        report = compare_release_surfaces(repository, policy)
    except (
        OSError,
        json.JSONDecodeError,
        SemverCompatibilityError,
        SyntaxError,
        tomllib.TOMLDecodeError,
        yaml.YAMLError,
    ) as error:
        print(f"semver compatibility failed: {error}")
        return 1
    if arguments.output is not None:
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
