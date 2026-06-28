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


def test_root_make_declares_shared_maintainer_commands() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert "check:" in root_make
    assert "sync-badges:" in root_make
    assert "check-badges:" in root_make


def test_root_security_dispatch_uses_isolated_package_environments() -> None:
    package_catalog = (
        REPO_ROOT / "makes" / "bijux-py" / "package-catalog.mk"
    ).read_text(encoding="utf-8")

    assert "ROOT_TARGET_SHARED_ENV_security ?= 0" in package_catalog
