from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_ingest_security_subtargets_bootstrap_package_environment() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-ingest.mk").read_text(
        encoding="utf-8"
    )

    assert "security-bandit" in profile
    assert "security-audit" in profile
    assert "security-deps" in profile


def test_index_typing_resolves_package_local_test_namespace() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-index.mk").read_text(
        encoding="utf-8"
    )

    assert "MYPY_FLAGS        := --strict --explicit-package-bases" in profile
    assert "export MYPYPATH   := $(CURDIR)/stubs:$(CURDIR)" in profile


def test_runtime_category_lanes_do_not_apply_unit_coverage_floors() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-runtime.mk").read_text(
        encoding="utf-8"
    )

    assert "test-e2e test-regression: PYTEST_ADDOPTS_EXTRA = --no-cov" in profile


def test_runtime_api_workspace_is_initialized_before_application_imports() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-runtime.mk").read_text(
        encoding="utf-8"
    )

    assert "api-test: api-test-workspace" in profile
    assert "openapi-drift: api-test-workspace" in profile
    assert (
        "api-test-workspace api-test openapi-drift api: export "
        "BIJUX_CANON_RUNTIME_WORKING_ROOT = $(API_TEST_WORKSPACE)"
    ) in profile
    assert "\nexport BIJUX_CANON_RUNTIME_WORKING_ROOT =" not in profile


def test_runtime_api_schema_path_is_rooted_after_shared_environment_loads() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "bijux-canon-runtime.mk").read_text(
        encoding="utf-8"
    )

    assert "override API_DIR = $(MONOREPO_ROOT)/apis/$(PROJECT_SLUG)/v2" in profile
    assert "RUNTIME_API_ROOT" not in profile


def test_compat_packages_install_security_tooling_without_stamp_shortcuts() -> None:
    profile = (REPO_ROOT / "makes" / "packages" / "compat-package.mk").read_text(
        encoding="utf-8"
    )

    assert "PACKAGE_INSTALL_STAMP ?=" not in profile
    assert "security-bandit" in profile
    assert "security-audit" in profile
    assert "security-deps" in profile
