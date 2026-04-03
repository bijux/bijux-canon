# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PROJECT_SLUG := bijux-canon-agent

include ../../makes/shared/python-package.mk

.NOTPARALLEL: all clean

LINT_DIRS            := src/bijux_canon_agent tests
MYPY_CONFIG          := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_FLAGS           := --follow-imports silent --ignore-missing-imports --strict-optional --disallow-untyped-defs --warn-return-any --check-untyped-defs
MYPY_TARGETS         := src/bijux_canon_agent/contracts src/bijux_canon_agent/pipeline src/bijux_canon_agent/tracing src/bijux_canon_agent/llm src/bijux_canon_agent/agents/base.py
MYPY_CORE_CONFIG     := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_CORE_FLAGS      := $(MYPY_FLAGS)
MYPY_CORE_TARGETS    := $(MYPY_TARGETS)
MYPY_EXTENDED_CONFIG := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_EXTENDED_FLAGS  := --follow-imports silent --ignore-missing-imports --strict-optional --no-warn-unused-ignores --no-warn-return-any --no-check-untyped-defs
MYPY_EXTENDED_TARGETS := src/bijux_canon_agent/agents src/bijux_canon_agent/application src/bijux_canon_agent/config src/bijux_canon_agent/interfaces src/bijux_canon_agent/observability src/bijux_canon_agent/pipeline src/bijux_canon_agent/reference_pipelines src/bijux_canon_agent/core tests
ENABLE_CODESPELL     := 1
ENABLE_RADON         := 1
ENABLE_PYDOCSTYLE    := 0
ENABLE_PYTYPE        := 1
RUFF_CHECK_FIX       := 1
INTERROGATE_PATHS    := src/bijux_canon_agent
QUALITY_PATHS        := src/bijux_canon_agent
QUALITY_PRE_TARGETS  := line_limit
QUALITY_MYPY_CONFIG  := $(MONOREPO_ROOT)/configs/mypy.ini
QUALITY_MYPY_FLAGS   := $(MYPY_FLAGS)
QUALITY_MYPY_TARGETS := $(MYPY_TARGETS)
SKIP_MYPY            := 0
QUALITY_VULTURE_MIN_CONFIDENCE := 90
SECURITY_PATHS       := src/bijux_canon_agent
SECURITY_IGNORE_IDS  := PYSEC-2022-42969 CVE-2026-21860
DOCS_DEV_ADDR        := 127.0.0.1:8000
DOCS_SITE_URL        := http://127.0.0.1:8000/
API_MODE             := contract
API_MODULE           := bijux_canon_agent.api
API_FACTORY          := create_app
API_SKIP_IF_NO_SCHEMAS := 1
API_LINT_MISSING_MESSAGE := → No API schemas found under $(API_DIR); skipping API lint
API_TEST_MISSING_MESSAGE := → No API schemas found under $(API_DIR); skipping API tests
API_NODE_BOOTSTRAP_MODE := npm-install-pinned
OPENAPI_GENERATOR_NPM_PACKAGE := @openapitools/openapi-generator-cli@2.27.0
OPENAPI_GENERATOR_JAR_VERSION := 7.18.0
API_VALIDATE_IN_NODE_DIR := 1
SCHEMATHESIS_OPTS    = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS    := 1
BUILD_CLEAN_PATHS    := build dist *.egg-info
BUILD_CLEAN_PYCACHE  := 1
PUBLISH_VERIFY_INSTALL_CMD := python -m bijux_canon_agent --help >/dev/null 2>&1
TEST_MAIN_ARGS       := -m "not integration and not e2e"
TEST_UNIT_DIR_ARGS   := -m "not integration and not e2e and not slow" --maxfail=1 -q
TEST_UNIT_FALLBACK_ARGS := -k "not e2e and not integration and not functional" -m "not integration and not e2e and not slow" --maxfail=1 -q
TEST_SYNTAX_PATHS    := src tests
TEST_PYCACHE_PREFIX  = $(TEST_ARTIFACTS_DIR)/pycache
TEST_RESET_PYCACHE   := 1
TEST_PRE_TARGETS     := bootstrap

# Modular Includes
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/docs.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/publish.mk

# Environment
$(VENV):
	@echo "→ Creating virtualenv with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv $(VENV)

install: $(VENV)
	@echo "→ Installing dependencies..."
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(VENV_PYTHON) -m pip install -e ".[dev]"

bootstrap: install
.PHONY: bootstrap

# Cleanup
clean:
	@$(MAKE) clean-soft
	@echo "→ Cleaning (.venv) ..."
	@$(RM) $(VENV)

clean-soft:
	@echo "→ Cleaning (no .venv) ..."
	@$(RM) \
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox demo .tmp_home \
	  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
	  spec.json openapitools.json node_modules site \
	  docs/reference artifacts "$(PROJECT_ARTIFACTS_DIR)" usage_test usage_test_artifacts .cache || true
	@$(RM) $(CONFIG_DIR)/.ruff_cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

# Pipelines
all: clean install test lint quality security api docs build sbom
	@echo "✔ All targets completed"

# Run independent checks in parallel
lint quality security api docs: | bootstrap
.NOTPARALLEL:

all-parallel: clean install
	@$(MAKE) -j4 quality security api docs
	@$(MAKE) build sbom
	@echo "✔ All targets completed (parallel mode)"

ci-fast: lint test mypy-core
.PHONY: ci-fast

line_limit:
	@$(VENV_PYTHON) "$(MONOREPO_ROOT)/scripts/bijux-canon-agent/check_line_limit.py"
.PHONY: line_limit

help:
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^##@/ {gsub(/^##@ */,""); print "\n\033[1m" $$0 "\033[0m"; next} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
.PHONY: help

##@ Core
clean: ## Remove virtualenv, caches, build, and artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run full pipeline (clean → sbom)
all-parallel: ## Run pipeline with parallelized lint, quality, security, api, and docs
help: ## Show this help
