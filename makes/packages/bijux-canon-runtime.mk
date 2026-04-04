# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package-profile.mk

PYTHON := python3.11

# ---- Single virtualenv (Python 3.11+) ----
ACT             := $(if $(wildcard $(VENV)/bin/activate),$(VENV)/bin,$(ACT))
LINT_DIRS       := src/bijux_canon_runtime
ENABLE_CODESPELL := 1
ENABLE_RADON    := 1
ENABLE_PYDOCSTYLE := 1
ENABLE_PYTYPE   := 0
LINT_PRE_TARGETS := ensure-venv
RUFF_CHECK_FIX  := 0
MYPY_FLAGS      := --strict --follow-imports silent
RADON_COMPLEXITY_MAX := 48
PYDOCSTYLE_ARGS := --convention=google --add-ignore=D100,D101,D102,D103,D104,D105,D106,D107
INTERROGATE_PATHS := src/bijux_canon_runtime
QUALITY_PATHS     := src/bijux_canon_runtime
QUALITY_MYPY_CONFIG := $(MONOREPO_ROOT)/configs/mypy.ini
QUALITY_MYPY_FLAGS := --strict --follow-imports silent
QUALITY_PRE_TARGETS := ensure-venv
SKIP_MYPY         := 0
QUALITY_VULTURE_MIN_CONFIDENCE := 90
SECURITY_PATHS     := src/bijux_canon_runtime
SECURITY_IGNORE_IDS := PYSEC-2022-42969 CVE-2025-68463
SECURITY_BANDIT_SKIP_IDS := B311
SECURITY_EXTRA_CHECKS := $(MONOREPO_ROOT)/packages/bijux-canon-dev/src/bijux_canon_dev/packages/runtime/check_dependency_allowlist.py
API_MODE := contract
API_BASE_PATH := /api/v1
API_MODULE := bijux_canon_runtime.api.v1.app
API_DYNAMIC_PORT := 1
OPENAPI_GENERATOR_NPM_PACKAGE := @openapitools/openapi-generator-cli@7.14.0
API_OPENAPI_DRIFT_COMMAND := $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_runtime.api.v1.app:app --schema "$(API_DIR)/v1/schema.yaml" --out "$(API_ARTIFACTS_DIR)/openapi.generated.json"
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,not_a_server_error --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS := 0
BUILD_TEMP_CLEAN_PATHS := $(COMMON_BUILD_CLEAN_PATHS) src/*.egg-info
BUILD_TEMP_CLEAN_PYCACHE := 1
BUILD_RELEASE_DRY_RUN_CMD := $(VENV_PYTHON) -c 'from packaging.version import Version; import importlib.metadata as m; from pathlib import Path; import sys; version=m.version("bijux-canon-runtime"); base=Version(version).base_version; print(f"version={version} base={base}"); changelog=Path("CHANGELOG.md").read_text().splitlines(); header=f"## {base}"; sys.exit(f"Missing changelog header for {base}") if header not in changelog else None; idx=changelog.index(header); section_lines=changelog[idx + 1:]; end_idx=next((i for i, line in enumerate(section_lines) if line.startswith("## ")), None); section="\n".join(section_lines[:end_idx] if end_idx is not None else section_lines); required=["### Added","### Changed","### Fixed"]; missing=[h for h in required if h not in section]; sys.exit(f"Changelog {base} missing sections: {missing}") if missing else None; print("✔ Changelog sections present")'
PUBLISH_UPLOAD_ENABLED := 0
TEST_PRE_TARGETS := ensure-venv
TEST_PATHS_E2E := tests/e2e
TEST_PATHS_REGRESSION := tests/regression
TEST_PATHS_EVALUATION := tests/regression
TEST_MAIN_ARGS := -m "not real_local and not api"
TEST_CI_TARGETS := test-unit test-e2e test-regression test-evaluation
TEST_REAL_LOCAL_PATH := tests/real_local
PACKAGE_DEFINE_INSTALL := 0
PACKAGE_DEFINE_CLEAN := 0
PACKAGE_ALL_TARGETS := clean install test lint quality security sbom build api
PACKAGE_HELP_WIDTH := 22

include $(ROOT_MAKE_DIR)/package-primary.mk

-include .env
export

.PHONY: install ensure-venv nlenv \
        clean clean-soft clean-venv \
        all help

PACKAGE_VENV_CREATE_MESSAGE := → Creating virtualenv at '$(VENV)' with '$$(which $(PYTHON))' ...
include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

##@ Core
ensure-venv: $(VENV) ## Ensure venv exists and deps are installed
	@set -e; \
	echo "→ Ensuring dependencies in $(VENV) ..."; \
	PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	"$(VENV_PYTHON)" -m pip install --upgrade pip setuptools wheel; \
	echo "→ Installing workspace runtime dependencies"; \
	"$(VENV_PYTHON)" -c 'from packaging.requirements import Requirement; from pathlib import Path; import tomllib; root = Path("$(MONOREPO_ROOT)"); workspace = tomllib.loads((root / "pyproject.toml").read_text()); package = tomllib.loads(Path("pyproject.toml").read_text()); package_dirs = workspace.get("tool", {}).get("bijux_canon", {}).get("package_dirs", {}); dependencies = package.get("project", {}).get("dependencies", []); current_name = package.get("project", {}).get("name"); [print(root / package_dirs[name]) for dep in dependencies if (name := Requirement(dep).name) != current_name and name in package_dirs]' | while IFS= read -r package_dir; do \
	  [ -n "$$package_dir" ] || continue; \
	  PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	  "$(VENV_PYTHON)" -m pip install -e "$$package_dir"; \
	done; \
	EXTRAS="$${EXTRAS:-dev}"; \
	if [ -n "$$EXTRAS" ]; then SPEC=".[$$EXTRAS]"; else SPEC="."; fi; \
	echo "→ Installing: $$SPEC"; \
	PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	"$(VENV_PYTHON)" -m pip install -e "$$SPEC"

install: ensure-venv ## Install project into .venv (dev)
	@true

nlenv: ## Print activate command
	@echo "Run: source $(ACT)/activate"

clean-soft: ## Remove build artifacts but keep venv
	@echo "→ Cleaning (no .venv removal) ..."
	@$(RM) \
	  $(COMMON_PYTHON_CLEAN_PATHS) demo .tmp_home \
	  $(COMMON_ARTIFACT_CLEAN_PATHS) || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

clean-venv: ## Remove the virtualenv only
	@echo "→ Cleaning ($(VENV)) ..."
	@$(RM) "$(VENV)"

clean: clean-soft clean-venv ## Remove venv + artifacts

all: ## Full pipeline
help: ## Show this help
