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


def test_root_pyproject_uses_shared_workspace_build_contract() -> None:
    pyproject = _root_pyproject()

    assert pyproject["build-system"] == {
        "requires": ["hatchling>=1.27.0,<1.30", "hatch-vcs>=0.4.0,<1.0"],
        "build-backend": "hatchling.build",
    }

    project = _as_dict(pyproject["project"])
    assert _as_str_list(project["dynamic"]) == ["version"]
    assert "version" not in project

    tool = _as_dict(pyproject["tool"])
    hatch = _as_dict(tool["hatch"])
    hatch_version = _as_dict(hatch["version"])
    assert hatch_version["source"] == "vcs"
    assert hatch_version["tag-pattern"] == "^v(?P<version>.*)$"

    uv_tool = _as_dict(tool["uv"])
    assert _as_dict(uv_tool["workspace"])["members"] == ["packages/*"]
    build_targets = _as_dict(_as_dict(hatch["build"])["targets"])
    assert _as_dict(build_targets["wheel"]) == {"bypass-selection": True}


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
