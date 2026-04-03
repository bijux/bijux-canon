# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

PROJECT_SLUG := bijux-llm-rar

include ../../makes/shared/python-package.mk

.NOTPARALLEL: all clean

LINT_DIRS         := src/bijux_rar
ENABLE_MYPY       := 0
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 1
ENABLE_PYDOCSTYLE := 0
ENABLE_PYTYPE     := 0
RUFF_CHECK_FIX    := 1
INTERROGATE_PATHS := src/bijux_rar
QUALITY_PATHS     := src/bijux_rar
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_rar
SECURITY_IGNORE_IDS := PYSEC-2022-42969
DOCS_DEV_ADDR     := 127.0.0.1:8000
DOCS_SITE_URL     := http://127.0.0.1:8000/
DOCS_DEPLOY_FLAGS := --force --no-history --clean --remote-branch gh-pages
API_MODE := contract
API_MODULE := bijux_rar.httpapi
API_INSTALL_EDITABLE := 1
API_NODE_BOOTSTRAP_MODE := npm-ci-sandbox
API_SCHEMATHESIS_FILTER_MODE := warnings
API_ENABLE_REPRO := 1
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := build dist *.egg-info
BUILD_CLEAN_PYCACHE := 1
PUBLISH_VERIFY_INSTALL_CMD := bijux --version
TEST_COVERAGE_TARGETS := $(abspath src/bijux_rar/core) $(abspath src/bijux_rar/boundaries)
TEST_MAIN_ARGS := --maxfail=1

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
	  find . -type f -name '*.pyc' -delete; \
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
