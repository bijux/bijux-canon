# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

PROJECT_SLUG := bijux-llm-flows
PYTHON := python3.11

include ../../makes/shared/python-package.mk

.NOTPARALLEL: all clean

# ---- Single virtualenv (Python 3.11+) ----
ACT             := $(if $(wildcard $(VENV)/bin/activate),$(VENV)/bin,$(ACT))
LINT_DIRS       := src/agentic_flows
ENABLE_CODESPELL := 1
ENABLE_RADON    := 1
ENABLE_PYDOCSTYLE := 1
ENABLE_PYTYPE   := 0
RUFF_CHECK_FIX  := 0
MYPY_FLAGS      := --strict --follow-imports silent
RADON_COMPLEXITY_MAX := 48
PYDOCSTYLE_ARGS := --convention=google --add-ignore=D100,D101,D102,D103,D104,D105,D106,D107
INTERROGATE_PATHS := src/agentic_flows
QUALITY_PATHS     := src/agentic_flows
QUALITY_MYPY_CONFIG := $(MONOREPO_ROOT)/configs/mypy.ini
QUALITY_MYPY_FLAGS := --strict --follow-imports silent
SKIP_MYPY         := 0
QUALITY_VULTURE_MIN_CONFIDENCE := 90
QUALITY_PYTHON_CHECKS := $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_md_links.py $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_docs_consistency.py $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_no_toys_policy.py
QUALITY_DOCS_LINK_SCRIPT := $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_md_links.py
QUALITY_RUN_MKDOCS := 1
SECURITY_PATHS     := src/agentic_flows
SECURITY_IGNORE_IDS := PYSEC-2022-42969 CVE-2025-68463
SECURITY_BANDIT_SKIP_IDS := B311
SECURITY_EXTRA_CHECKS := $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_dependency_allowlist.py
API_MODE := contract
API_BASE_PATH := /api/v1
API_MODULE := agentic_flows.http_api.app
API_DYNAMIC_PORT := 1
OPENAPI_GENERATOR_NPM_PACKAGE := @openapitools/openapi-generator-cli@7.14.0
API_OPENAPI_DRIFT_CHECK := $(MONOREPO_ROOT)/scripts/bijux-llm-flows/check_openapi_drift.py
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,not_a_server_error --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS := 0
BUILD_TEMP_CLEAN_PATHS := build dist src/*.egg-info
BUILD_TEMP_CLEAN_PYCACHE := 1
BUILD_RELEASE_DRY_RUN_CMD := $(VENV_PYTHON) -c 'from packaging.version import Version; import importlib.metadata as m; from pathlib import Path; import sys; version=m.version("bijux-llm-flows"); base=Version(version).base_version; print(f"version={version} base={base}"); changelog=Path("CHANGELOG.md").read_text().splitlines(); header=f"## {base}"; sys.exit(f"Missing changelog header for {base}") if header not in changelog else None; idx=changelog.index(header); section_lines=changelog[idx + 1:]; end_idx=next((i for i, line in enumerate(section_lines) if line.startswith("## ")), None); section="\n".join(section_lines[:end_idx] if end_idx is not None else section_lines); required=["### Added","### Changed","### Fixed"]; missing=[h for h in required if h not in section]; sys.exit(f"Changelog {base} missing sections: {missing}") if missing else None; print("✔ Changelog sections present")'
PUBLISH_UPLOAD_ENABLED := 0
TEST_PRE_TARGETS := ensure-venv
TEST_PATHS_E2E := tests/e2e
TEST_PATHS_REGRESSION := tests/regression
TEST_PATHS_EVALUATION := tests/regression
TEST_MAIN_ARGS := -m "not real_local and not api"
TEST_CI_TARGETS := test-unit test-e2e test-regression test-evaluation
TEST_REAL_LOCAL_PATH := tests/real_local

# ---- Includes ----
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/docs.mk
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/publish.mk

-include .env
export

.PHONY: install ensure-venv nlenv \
        clean clean-soft clean-venv \
        manage_examples manage_models \
        all help

$(VENV):
	@echo "→ Creating virtualenv at '$(VENV)' with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv "$(VENV)"

ensure-venv: $(VENV) ## Ensure venv exists and deps are installed
	@set -e; \
	echo "→ Ensuring dependencies in $(VENV) ..."; \
	PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	"$(VENV_PYTHON)" -m pip install --upgrade pip setuptools wheel; \
	echo "→ Installing workspace runtime dependencies"; \
	"$(VENV_PYTHON)" -c 'from packaging.requirements import Requirement; from pathlib import Path; import tomllib; root = Path("$(MONOREPO_ROOT)"); workspace = tomllib.loads((root / "pyproject.toml").read_text()); package = tomllib.loads(Path("pyproject.toml").read_text()); package_dirs = workspace.get("tool", {}).get("bijux_llm_nexus", {}).get("package_dirs", {}); dependencies = package.get("project", {}).get("dependencies", []); current_name = package.get("project", {}).get("name"); [print(root / package_dirs[name]) for dep in dependencies if (name := Requirement(dep).name) != current_name and name in package_dirs]' | while IFS= read -r package_dir; do \
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
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox demo .tmp_home \
	  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
	  artifacts "$(PROJECT_ARTIFACTS_DIR)" .cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

clean-venv:
	@echo "→ Cleaning ($(VENV)) ..."
	@$(RM) "$(VENV)"

clean: clean-soft clean-venv ## Remove venv + artifacts

all: clean install test lint quality security sbom build docs api ## Full pipeline
	@echo "✔ All targets completed"

manage_examples:
	@echo "manage_examples has no root script implementation."
	@exit 1

manage_models:
	@echo "manage_models has no root script implementation."
	@exit 1

help: ## Show this help
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
