"""Resolve editable workspace and external package installation inputs."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import NormalizedName, canonicalize_name

from bijux_canon_dev.release.wheel_inventory import (
    PackagePolicy,
    WheelInventoryError,
    inspect_workspace_policy,
)


class WorkspaceInstallError(RuntimeError):
    """Workspace package metadata cannot produce a safe installation plan."""


@dataclass(frozen=True)
class WorkspaceInstallPlan:
    """External requirements and editable local paths for one package."""

    external_requirements: tuple[str, ...]
    local_paths: tuple[Path, ...]


def _selected_requirements(
    policy: PackagePolicy, extras: Sequence[str]
) -> tuple[str, ...]:
    optional = dict(policy.optional_dependencies)
    selected = tuple(
        dict.fromkeys(
            canonicalize_name(extra.strip()) for extra in extras if extra.strip()
        )
    )
    unknown = sorted(set(selected) - set(optional))
    if unknown:
        raise WorkspaceInstallError(
            f"unknown extras for {policy.distribution_name}: {', '.join(unknown)}"
        )
    values = list(policy.dependencies)
    for extra in selected:
        values.extend(optional[extra])
    return tuple(values)


def _requirement_name(value: str, *, distribution: str) -> NormalizedName:
    try:
        return canonicalize_name(Requirement(value).name)
    except InvalidRequirement as exc:
        raise WorkspaceInstallError(
            f"invalid requirement for {distribution}: {value}"
        ) from exc


def resolve_workspace_install(
    repo_root: Path,
    package_dir: Path,
    extras: Sequence[str] = ("dev",),
) -> WorkspaceInstallPlan:
    """Resolve one package's external requirements and editable workspace peers."""
    repo_root = repo_root.resolve()
    package_dir = package_dir.resolve()
    policies = inspect_workspace_policy(repo_root)
    matches = [
        policy
        for policy in policies
        if policy.pyproject_path.parent.resolve() == package_dir
    ]
    if len(matches) != 1:
        raise WorkspaceInstallError(
            f"package directory is not uniquely declared by the workspace: {package_dir}"
        )
    target = matches[0]
    workspace = {
        canonicalize_name(policy.distribution_name): policy for policy in policies
    }
    target_name = canonicalize_name(target.distribution_name)
    external: list[str] = []
    local: dict[str, Path] = {}

    for value in _selected_requirements(target, extras):
        name = _requirement_name(value, distribution=target.distribution_name)
        if name == target_name:
            continue
        peer = workspace.get(name)
        if peer is None:
            external.append(value)
        else:
            local[name] = peer.pyproject_path.parent.resolve()

    for value in target.dynamic_dependency_names:
        name = canonicalize_name(value)
        peer = workspace.get(name)
        if peer is None:
            raise WorkspaceInstallError(
                f"unknown dynamic workspace dependency for "
                f"{target.distribution_name}: {value}"
            )
        if name != target_name:
            local[name] = peer.pyproject_path.parent.resolve()

    unique_external = tuple(
        sorted(
            dict.fromkeys(external),
            key=lambda value: (
                _requirement_name(value, distribution=target.distribution_name),
                value,
            ),
        )
    )
    return WorkspaceInstallPlan(
        external_requirements=unique_external,
        local_paths=tuple(local[name] for name in sorted(local)),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve workspace and external dependencies for a package install."
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--kind", choices=("external", "local"), required=True)
    parser.add_argument("--extras", default="dev")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Print one installation input per line for consumption by Make."""
    arguments = _parser().parse_args(argv)
    try:
        plan = resolve_workspace_install(
            arguments.repo,
            arguments.package_dir,
            arguments.extras.split(","),
        )
    except (WheelInventoryError, WorkspaceInstallError) as exc:
        raise SystemExit(str(exc)) from exc
    values: Sequence[str | Path]
    if arguments.kind == "external":
        values = plan.external_requirements
    else:
        values = plan.local_paths
    for value in values:
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
