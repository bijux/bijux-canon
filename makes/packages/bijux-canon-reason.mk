# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
PACKAGE_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PROJECT_SLUG := bijux-canon-reason

include $(PACKAGE_MAKEFILE_DIR)/../env.mk

LINT_DIRS         := src/bijux_canon_reason
ENABLE_MYPY       := 0
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 1
ENABLE_PYDOCSTYLE := 0
ENABLE_PYTYPE     := 0
RUFF_CHECK_FIX    := 1
INTERROGATE_PATHS := src/bijux_canon_reason
QUALITY_PATHS     := src/bijux_canon_reason
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_canon_reason
SECURITY_IGNORE_IDS := PYSEC-2022-42969
API_MODE := contract
API_MODULE := bijux_canon_reason.api.v1.app
API_INSTALL_EDITABLE := 1
API_NODE_BOOTSTRAP_MODE := npm-ci-sandbox
API_SCHEMATHESIS_FILTER_MODE := warnings
API_ENABLE_REPRO := 1
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := build dist *.egg-info
BUILD_CLEAN_PYCACHE := 1
PUBLISH_VERIFY_INSTALL_CMD := bijux --version
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_reason/core) $(abspath src/bijux_canon_reason/interfaces)
TEST_MAIN_ARGS := --maxfail=1
ENABLE_BENCH := 0
PACKAGE_BOOTSTRAP_TARGETS := lint quality security api
PACKAGE_CLEAN_PATHS := \
  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox demo .tmp_home \
  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
  spec.json openapitools.json node_modules site \
  docs/reference artifacts "$(PROJECT_ARTIFACTS_DIR)" usage_test usage_test_artifacts .cache \
  "$(CONFIG_DIR)/.ruff_cache"
PACKAGE_ALL_TARGETS := clean install test lint quality security api build sbom

# Modular Includes
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/publish.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

# Run independent checks in parallel
.NOTPARALLEL:

all-parallel: clean install
	@$(MAKE) -j4 quality security api
	@$(MAKE) build sbom
	@echo "✔ All targets completed (parallel mode)"

##@ Core
clean: ## Remove virtualenv, caches, build, and artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run full pipeline (clean → sbom)
all-parallel: ## Run pipeline with parallelized lint, quality, security, and api
help: ## Show this help
