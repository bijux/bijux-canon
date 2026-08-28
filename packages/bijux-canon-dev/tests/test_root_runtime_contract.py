from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path
import subprocess

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


def test_package_tox_constrains_installs_to_the_workspace_lock() -> None:
    config = _tox_config()["testenv"]
    environment = config["setenv"]

    assert (
        "UV_CONSTRAINT = {tox_root}/artifacts/root/tox/locked-constraints.txt"
        in environment
    )
    assert (
        "PIP_CONSTRAINT = {tox_root}/artifacts/root/tox/locked-constraints.txt"
        in environment
    )
    assert "uv-lock-constraints.sh" in config["commands_pre"]
    assert "uv-lock-constraints.sh" in config["allowlist_externals"]


def test_package_tox_keeps_verification_read_only_and_caches_contained() -> None:
    environment = _tox_config()["testenv"]["setenv"]

    assert "RUFF_CHECK_FIX=0" in environment
    assert "FMT_RUN_RUFF_CHECK_FIX=0" in environment
    assert (
        "PROJECT_ARTIFACTS_DIR={tox_root}/artifacts/root/tox/package-artifacts/{env_name}"
        in environment
    )
    assert (
        "PROJECT_ARTIFACTS_DIR = "
        "{tox_root}/artifacts/root/tox/package-artifacts/{env_name}" in environment
    )
    assert (
        "PYTHONPYCACHEPREFIX = {tox_root}/artifacts/root/tox/pycache/{env_name}"
        in environment
    )
    assert "EXTRAS={env:INSTALL_EXTRAS}" in environment
    assert "WORKSPACE_EDITABLE_EXTRAS={env:INSTALL_EXTRAS}" in environment
    assert "PACKAGE_INSTALL_SPEC=.[{env:INSTALL_EXTRAS}]" in environment


def test_package_tox_installs_extras_exercised_by_runtime_and_index_tests() -> None:
    environment = _tox_config()["testenv"]["setenv"]

    assert "test-runtime: INSTALL_EXTRAS = dev,local-cpu" in environment
    assert "index: INSTALL_EXTRAS = dev,vdb" in environment


def test_index_build_does_not_reformat_the_submitted_source() -> None:
    index_make = (REPO_ROOT / "makes" / "packages" / "bijux-canon-index.mk").read_text(
        encoding="utf-8"
    )

    build_prerequisites = next(
        line for line in index_make.splitlines() if line.startswith("BUILD_PRE_TARGETS")
    )
    assert "fmt" not in build_prerequisites.split(":=", 1)[1].split()


def test_index_verification_installs_exercised_vdb_dependencies() -> None:
    index_make = (REPO_ROOT / "makes" / "packages" / "bijux-canon-index.mk").read_text(
        encoding="utf-8"
    )

    assert "PACKAGE_INSTALL_SPEC := .[dev,vdb]" in index_make.splitlines()


def test_recursive_gate_prerequisites_propagate_failures(tmp_path: Path) -> None:
    marker = tmp_path / "unexpected-success"
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        "\n".join(
            (
                f"include {REPO_ROOT / 'makes' / 'bijux-py' / 'ci' / 'util.mk'}",
                ".PHONY: all fail pass",
                "all:",
                "\t$(call run_make_targets,fail pass,$(MAKE))",
                "fail:",
                "\t@exit 7",
                "pass:",
                f"\t@touch {marker}",
            )
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["make", "-f", str(makefile), "all"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not marker.exists()


def test_package_artifact_build_stops_at_the_first_failed_command(
    tmp_path: Path,
) -> None:
    package_dir = REPO_ROOT / "packages" / "bijux-canon-index"
    result = subprocess.run(
        [
            "make",
            "-f",
            str(REPO_ROOT / "makes" / "packages" / "bijux-canon-index.mk"),
            "build-package",
            "BUILD_PRE_TARGETS=",
            "BUILD_POST_TARGETS=",
            "BUILD_TOOLS_COMMAND=true",
            "BUILD_PYTHON=false",
            "BUILD_CHECK_DISTS=0",
            "PACKAGE_DIR=.",
            "VENV_PYTHON=/usr/bin/true",
            f"PROJECT_ARTIFACTS_DIR={tmp_path / 'artifacts'}",
        ],
        cwd=package_dir,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Package artifacts ready" not in result.stdout


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
