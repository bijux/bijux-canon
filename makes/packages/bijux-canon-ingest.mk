# SPDX-License-Identifier: Apache-2.0

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk

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
BUILD_CLEAN_PATHS              := $(COMMON_BUILD_CLEAN_PATHS)
PUBLISH_UPLOAD_ENABLED         := 0
PACKAGE_CLEAN_PATHS := \
  $(COMMON_PYTHON_CLEAN_PATHS) \
  $(COMMON_ARTIFACT_CLEAN_PATHS) site
PACKAGE_INSTALL_TARGETS := \
  test lint fmt quality security api build sbom \
  fmt-artifacts lint-artifacts interrogate-report
PACKAGE_ALL_TARGETS := clean install test lint quality security api build sbom

include $(ROOT_MAKE_DIR)/package/gates.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

