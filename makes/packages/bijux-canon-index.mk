# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# Testing policy: gates (lint/quality/security/typing) intentionally run on lowest supported Python (3.11); full matrix via tox.

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package-profile.mk

PYTHON := python3.11

LINT_DIRS         := src/bijux_canon_index
FMT_DIRS          := src tests
ENABLE_MYPY       := 0
ENABLE_CODESPELL  := 1
CODESPELL         := $(if $(ACT),$(ACT)/codespell,codespell) --ignore-words-list=ND,nd
ENABLE_RADON      := 1
ENABLE_PYDOCSTYLE := 0
ENABLE_PYTYPE     := 0
RUFF_CHECK_FIX    := 1
INTERROGATE_PATHS := src/bijux_canon_index
QUALITY_PATHS     := src/bijux_canon_index
QUALITY_VULTURE_MIN_CONFIDENCE := 80
QUALITY_CLEAN_SITE := 1
SECURITY_PATHS    := src/bijux_canon_index
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SECURITY_AUDIT_PREPARE_MODE := pyproject
PIP_AUDIT_INPUTS = -r "$(SECURITY_REQS)"
DOCS_DEV_ADDR    := 0.0.0.0:8000
DOCS_EXTRA_CLEAN_PATHS := site docs/site
API_MODE         := freeze
API_LOG          = $(API_ARTIFACTS_DIR)/openapi_drift.log
API_DRIFT_COMMAND = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_index.api.v1:build_app --schema "$(API_SCHEMA_YAML)" --out "$(API_ARTIFACTS_DIR)/openapi.generated.json"
PUBLISH_DIST_DIR := $(PROJECT_ARTIFACTS_DIR)/release
PUBLISH_UPLOAD_ENABLED := 0
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_index/core) $(abspath src/bijux_canon_index/contracts) $(abspath src/bijux_canon_index/domain)
TEST_MAIN_ARGS := --maxfail=1
PACKAGE_VENV_CREATE_MESSAGE := [INFO] Creating virtualenv with '$$(which $(PYTHON))' ...
PACKAGE_INSTALL_MESSAGE := [INFO] Installing dependencies...
PACKAGE_CLEAN_MESSAGE := [INFO] Cleaning (.venv) ...
PACKAGE_CLEAN_SOFT_MESSAGE := [INFO] Cleaning (no .venv) ...
PACKAGE_BOOTSTRAP_PREREQS := $(VENV)
PACKAGE_BOOTSTRAP_TARGETS := lint quality security api docs
PACKAGE_CLEAN_PATHS := \
  $(COMMON_PYTHON_CLEAN_PATHS) \
  $(COMMON_API_TEMP_CLEAN_PATHS) session.sqlite \
  docs/site $(COMMON_ARTIFACT_CLEAN_PATHS) $(COMMON_CONFIG_CACHE_CLEAN_PATHS)
PACKAGE_ALL_TARGETS := clean install fmt lint test quality api security sbom
PACKAGE_ALL_MESSAGE := [OK] All targets completed

# Modular Includes
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/publish.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

# Run independent checks in parallel
.NOTPARALLEL:

release: clean install fmt lint test quality security sbom
	@echo "[INFO] Building release artifacts"
	@mkdir -p "$(PROJECT_ARTIFACTS_DIR)/release"
	@$(VENV_PYTHON) -m build --wheel --sdist --outdir "$(PROJECT_ARTIFACTS_DIR)/release"
	@echo "[INFO] Generating SBOM"
	@if ! command -v $(PIP_AUDIT) >/dev/null 2>&1; then \
	  echo "→ Installing pip-audit into $(VENV)"; \
	  $(VENV_PYTHON) -m pip install --upgrade pip-audit >/dev/null; \
	fi
	@$(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output "$(PROJECT_ARTIFACTS_DIR)/release/sbom.json" || true
	@echo "[INFO] Refreshing pinned OpenAPI v1"
	@$(VENV_PYTHON) -c 'from pathlib import Path; import json; from bijux_canon_index.api.v1 import build_app; output = Path("$(API_DIR)/v1/pinned_openapi.json"); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(build_app().openapi(), indent=2, sort_keys=True), encoding="utf-8")'
	@cd "$(PROJECT_ARTIFACTS_DIR)/release" && shasum -a 256 *.whl *.tar.gz > SHA256SUMS
	@echo "[OK] Release artifacts ready under $(PROJECT_ARTIFACTS_DIR)/release"

build: release
	@echo "[OK] build target completed (alias for make release)"

include $(ROOT_MAKE_DIR)/package-core-help.mk
