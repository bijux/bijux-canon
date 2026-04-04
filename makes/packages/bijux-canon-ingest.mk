# SPDX-License-Identifier: Apache-2.0

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
PACKAGE_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PROJECT_SLUG := bijux-canon-ingest

include $(PACKAGE_MAKEFILE_DIR)/../env.mk

LINT_DIRS                      := src tests stubs
RUFF_CONFIG                    := pyproject.toml
MYPY_TARGETS                   = $(if $(LINT_SCOPE),$(LINT_SCOPE),src/bijux_canon_ingest)
MYPY_CONFIG                    := pyproject.toml
MYPY_FLAGS                     :=
ENABLE_CODESPELL               := 0
ENABLE_RADON                   := 0
ENABLE_PYDOCSTYLE              := 0
FMT_RUN_RUFF_CHECK_FIX         := 1
INTERROGATE_PATHS              := src/bijux_canon_ingest
QUALITY_PATHS                  := src/bijux_canon_ingest
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS                 := src/bijux_canon_ingest
SECURITY_IGNORE_IDS            := PYSEC-2022-42969
SECURITY_BANDIT_SKIP_IDS       := B101,B311
BANDIT_FLAGS                   := --severity-level high --confidence-level high
BANDIT_EXCLUDES                := .venv,venv,build,dist,.tox,.mypy_cache,.pytest_cache,tests
PIP_AUDIT_CONSOLE_FLAGS        := --progress-spinner off
API_MODE                       := live-contract
API_SCHEMA                     := $(API_DIR)/v1/schema.yaml
API_SERVER_IMPORT              := bijux_canon_ingest.interfaces.http.app:create_app
API_DRIFT_OUT                  = $(API_ARTIFACTS_DIR)/openapi.generated.json
API_DRIFT_COMMAND              = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_ingest.interfaces.http.app:create_app --schema "$(API_SCHEMA)" --out "$(API_DRIFT_OUT)"
BUILD_CHECK_DISTS              := 1
BUILD_CLEAN_PATHS              := dist build *.egg-info
PUBLISH_UPLOAD_ENABLED         := 0
PACKAGE_CLEAN_PATHS := \
  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox .nox \
  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
  artifacts "$(PROJECT_ARTIFACTS_DIR)" site .cache
PACKAGE_INSTALL_TARGETS := \
  test lint fmt quality security api build sbom \
  fmt-artifacts lint-artifacts interrogate-report
PACKAGE_ALL_TARGETS := clean install test lint quality security api build sbom

include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/publish.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

##@ Core
clean: ## Remove virtualenv plus caches/artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run clean → install → test → lint
help: ## Show this help
