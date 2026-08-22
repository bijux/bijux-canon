from __future__ import annotations

from pathlib import Path
import tomllib
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[3]
PROTEOMICS_ONLY_EXTENSION_COMMANDS = {
    "ensure-venv:",
    "nlenv:",
    "manage_examples:",
    "manage_models:",
    "api-freeze:",
    "openapi-drift:",
    "architecture-check:",
}


def _as_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], value)


def _root_pyproject() -> dict[str, object]:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return cast(dict[str, object], tomllib.load(handle))


def test_root_pyproject_declares_shared_quality_tooling() -> None:
    tool_section = _as_dict(_root_pyproject()["tool"])
    interrogate = _as_dict(tool_section["interrogate"])
    bandit = _as_dict(tool_section["bandit"])

    assert interrogate == {"fail-under": 32, "color": True}
    assert bandit == {
        "exclude_dirs": [
            ".venv",
            "tests",
            "artifacts",
            ".pytest_cache",
            ".ruff_cache",
        ],
    }


def test_security_tooling_has_no_ungoverned_suppressions() -> None:
    security_make = (REPO_ROOT / "makes" / "bijux-py" / "ci" / "security.mk").read_text(
        encoding="utf-8"
    )
    sbom_make = (REPO_ROOT / "makes" / "bijux-py" / "ci" / "sbom.mk").read_text(
        encoding="utf-8"
    )

    assert "SECURITY_IGNORE_IDS           ?=\n" in security_make
    assert "SECURITY_BANDIT_SKIP_IDS      ?=\n" in security_make
    assert "Ungoverned dependency vulnerability suppressions are forbidden" in (
        security_make
    )
    assert "Ungoverned Bandit suppressions are forbidden" in security_make
    assert "Bandit is mandatory; SKIP_BANDIT must remain 0" in security_make
    assert "Dependency vulnerability auditing is mandatory and strict" in security_make
    assert "SBOM_IGNORE_IDS          ?=\n" in sbom_make
    assert "Ungoverned SBOM vulnerability suppressions are forbidden" in sbom_make
    assert '--output "$(SBOM_PROD_FILE)" || true' not in sbom_make
    assert '--output "$(SBOM_DEV_FILE)" || true' not in sbom_make


def test_root_dead_code_gate_is_fatal_and_uses_an_owned_whitelist() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert "quality: quality-dead-code" in root_make
    assert '"$(ROOT_CHECK_PYTHON)" -m vulture' in root_make
    assert '"$(ROOT_VULTURE_WHITELIST)" --min-confidence 100' in root_make
    assert "|| true" not in root_make.split("quality-dead-code:", 1)[1]
    assert (REPO_ROOT / "configs" / "vulture_whitelist.py").is_file()


def test_root_checks_preserve_the_locked_shared_environment() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert "$(UV_SYNC) >/dev/null" in root_make
    assert "PACKAGE_BOOTSTRAP_TARGETS=" in root_make
    assert "PACKAGE_INSTALL_TARGETS=" in root_make
    assert "LINT_PRE_TARGETS=" in root_make


def test_root_pytest_environment_keeps_generated_state_under_artifacts() -> None:
    root_environment = (REPO_ROOT / "makes" / "bijux-py" / "root" / "env.mk").read_text(
        encoding="utf-8"
    )
    package_dispatch = (
        REPO_ROOT / "makes" / "bijux-py" / "root" / "package-dispatch.mk"
    ).read_text(encoding="utf-8")
    pytest_configuration = (REPO_ROOT / "configs" / "pytest.ini").read_text(
        encoding="utf-8"
    )

    assert "ROOT_PYCACHE_DIR ?= $(ROOT_ARTIFACTS_DIR)/pycache" in root_environment
    assert "export PYTHONDONTWRITEBYTECODE := 1" in root_environment
    assert (
        "export PYTHONPYCACHEPREFIX := $(abspath $(ROOT_PYCACHE_DIR))"
        in root_environment
    )
    assert "artifacts/$(1)/pycache" in package_dispatch
    assert "cache_dir = ../artifacts/root/pytest-cache" in pytest_configuration


def test_root_pyproject_uses_only_the_shared_dev_group() -> None:
    dependency_groups = _as_dict(_root_pyproject()["dependency-groups"])
    assert set(dependency_groups) == {"dev"}


def test_root_make_does_not_declare_proteomics_only_extensions() -> None:
    root_make = (REPO_ROOT / "makes" / "root.mk").read_text(encoding="utf-8")

    assert not any(
        command in root_make for command in PROTEOMICS_ONLY_EXTENSION_COMMANDS
    )
