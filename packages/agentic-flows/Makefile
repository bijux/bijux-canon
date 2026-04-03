# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

PROJECT_SLUG := agentic-flows
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
RADON_COMPLEXITY_MAX := 48
PYDOCSTYLE_ARGS := --convention=google --add-ignore=D100,D101,D102,D103,D104,D105,D106,D107
INTERROGATE_PATHS := src/agentic_flows
QUALITY_PATHS     := src/agentic_flows
QUALITY_MYPY_CONFIG := $(CONFIG_DIR)/mypy.ini
QUALITY_MYPY_FLAGS := --strict
SKIP_MYPY         := 0
QUALITY_VULTURE_MIN_CONFIDENCE := 90
QUALITY_PYTHON_CHECKS := $(MONOREPO_ROOT)/scripts/agentic-flows/check_md_links.py $(MONOREPO_ROOT)/scripts/agentic-flows/check_docs_consistency.py $(MONOREPO_ROOT)/scripts/agentic-flows/check_no_toys_policy.py
QUALITY_DOCS_LINK_SCRIPT := $(MONOREPO_ROOT)/scripts/agentic-flows/check_md_links.py
QUALITY_RUN_MKDOCS := 1
SECURITY_PATHS     := src/agentic_flows
SECURITY_IGNORE_IDS := PYSEC-2022-42969 CVE-2025-68463
SECURITY_BANDIT_SKIP_IDS := B311
SECURITY_EXTRA_CHECKS := $(MONOREPO_ROOT)/scripts/agentic-flows/check_dependency_allowlist.py
PUBLISH_UPLOAD_ENABLED := 0
TEST_PRE_TARGETS := ensure-venv
TEST_PATHS_E2E := tests/e2e
TEST_PATHS_REGRESSION := tests/regression
TEST_PATHS_EVALUATION := tests/regression
TEST_MAIN_ARGS := -m "not real_local"
TEST_CI_TARGETS := test-unit test-e2e test-regression test-evaluation
TEST_REAL_LOCAL_PATH := tests/real_local

# ---- Includes ----
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/docs.mk
include $(MAKE_DIR)/api.mk
include $(MAKE_DIR)/architecture.mk
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
	  .ruff_cache .mypy_cache .pytype .hypothesis .coverage.* .coverage .benchmarks \
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
