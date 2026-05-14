from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _deptry_config() -> dict[str, object]:
    with (REPO_ROOT / "configs" / "deptry.toml").open("rb") as handle:
        return cast(dict[str, object], tomllib.load(handle))


def test_root_deptry_configuration_uses_supported_dev_group_contract() -> None:
    tool = _as_dict(_deptry_config()["tool"])
    deptry_config = _as_dict(tool["deptry"])

    assert deptry_config["optional_dependencies_dev_groups"] == ["dev"]
    assert "pep621_dev_dependency_groups" not in deptry_config
    assert deptry_config["ignore"] == ["DEP003"]
    assert deptry_config["extend_exclude"] == ["docs", "apis", "artifacts", "site"]


def test_package_override_deptry_configuration_uses_supported_dev_group_contract() -> (
    None
):
    tool = _as_dict(_deptry_config()["tool"])
    repo_deptry = _as_dict(tool["repo_deptry"])
    packages = _as_dict(repo_deptry["packages"])
    ingest_override = _as_dict(packages["bijux-canon-ingest"])

    assert ingest_override["optional_dependencies_dev_groups"] == ["dev", "docs"]
    assert "pep621_dev_dependency_groups" not in ingest_override
