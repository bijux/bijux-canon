from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _tox_config() -> ConfigParser:
    parser = ConfigParser()
    parser.read(REPO_ROOT / "tox.ini", encoding="utf-8")
    return parser


def _envlist() -> set[str]:
    envlist = _tox_config()["tox"]["envlist"]
    return {line.strip() for line in envlist.splitlines() if line.strip()}


def test_root_tox_declares_shared_env_families() -> None:
    envlist = _envlist()

    assert "security" in envlist
    assert "docs" in envlist
    assert (
        "test-{dev,runtime,agent,ingest,reason,index,compatcanon,compatflows,compatagent,compatrag,compatrar,compatvex}"
        in envlist
    )
    assert (
        "lint-{dev,runtime,agent,ingest,reason,index,compatcanon,compatflows,compatagent,compatrag,compatrar,compatvex}"
        in envlist
    )
    assert (
        "quality-{dev,runtime,agent,ingest,reason,index,compatcanon,compatflows,compatagent,compatrag,compatrar,compatvex}"
        in envlist
    )
    assert (
        "security-{dev,runtime,agent,ingest,reason,index,compatcanon,compatflows,compatagent,compatrag,compatrar,compatvex}"
        in envlist
    )
    assert "fmt-{dev,runtime,agent,ingest,reason,index}" not in envlist
    assert "api-freeze-core" not in envlist
    assert "openapi-drift-core" not in envlist
    assert _tox_config()["tox"]["isolated_build"] == "true"
    assert "tox-gh-actions>=3.1" in _tox_config()["tox"]["requires"]
    assert _tox_config()["tox"]["toxworkdir"] == "{tox_root}/artifacts/root/tox"


def test_root_tox_supports_pip_26_bootstrap_contract() -> None:
    config = _tox_config()
    pip_requirement = '"pip>=25.3,<27"'

    assert pip_requirement in config["testenv"]["commands_pre"]
    assert pip_requirement in config["testenv:security"]["commands_pre"]
    assert pip_requirement in config["testenv:docs"]["commands_pre"]


def test_package_tox_uses_cached_uv_install_fallback() -> None:
    environment = _tox_config()["testenv"]["setenv"]

    assert "UV = {tox_root}/makes/tooling/uv-cache-fallback.sh" in environment


def test_root_make_declares_shared_maintainer_commands() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert "check:" in root_make
    assert "sync-badges:" in root_make
    assert "check-badges:" in root_make


def test_root_security_dispatch_uses_isolated_package_environments() -> None:
    package_inventory = (REPO_ROOT / "makes" / "packages.mk").read_text(
        encoding="utf-8"
    )

    assert "ROOT_TARGET_SHARED_ENV_security := 0" in package_inventory
