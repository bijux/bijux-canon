from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_TOOL = "bijux_canon"


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _as_str_list(value: object) -> list[str]:
    return cast(list[str], value)


def _root_pyproject() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return cast(dict[str, object], tomllib.load(handle))


def _workspace_distribution_names() -> set[str]:
    tool = _as_dict(_root_pyproject()["tool"])
    workspace = _as_dict(tool[WORKSPACE_TOOL])
    distribution_names: set[str] = set()

    for package_dir in _as_dict(workspace["package_dirs"]).values():
        with (REPO_ROOT / cast(str, package_dir) / "pyproject.toml").open(
            "rb"
        ) as handle:
            package_pyproject = cast(dict[str, object], tomllib.load(handle))
        project = _as_dict(package_pyproject["project"])
        distribution_names.add(cast(str, project["name"]))

    return distribution_names


def test_root_pyproject_keeps_distribution_builds_in_workspace_packages() -> None:
    pyproject = _root_pyproject()
    tool = _as_dict(pyproject["tool"])
    assert "project" not in pyproject
    assert "build-system" not in pyproject
    assert "hatch" not in tool
    assert _as_dict(_as_dict(tool["uv"])["workspace"])["members"] == ["packages/*"]
    package_paths = sorted((REPO_ROOT / "packages").glob("*/pyproject.toml"))
    workspace = _as_dict(tool[WORKSPACE_TOOL])
    assert {
        path.parent.relative_to(REPO_ROOT).as_posix() for path in package_paths
    } == set(_as_dict(workspace["package_dirs"]).values())
    names = []
    for path in package_paths:
        package = tomllib.loads(path.read_text())
        names.append(package["project"]["name"])
        assert "build-system" in package
    assert set(names) == _workspace_distribution_names()
    assert len(names) == len(set(names))


def test_root_pyproject_exposes_all_workspace_packages_to_root_dev_installs() -> None:
    pyproject = _root_pyproject()
    dependency_groups = _as_dict(pyproject["dependency-groups"])
    dev_group = _as_str_list(dependency_groups["dev"])
    dev_group_entries = {entry.split("[", 1)[0] for entry in dev_group}

    assert dev_group_entries.issuperset(_workspace_distribution_names())


def test_root_pyproject_uses_workspace_sources_for_every_workspace_package() -> None:
    pyproject = _root_pyproject()
    workspace_packages = _workspace_distribution_names()
    tool = _as_dict(pyproject["tool"])
    uv_sources = _as_dict(_as_dict(tool["uv"])["sources"])

    assert set(uv_sources) == workspace_packages
    assert {
        name
        for name, config in uv_sources.items()
        if _as_dict(config) == {"workspace": True}
    } == (workspace_packages)
