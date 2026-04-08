# Testing policy: gates (lint/quality/security/typing) intentionally run on lowest supported Python (3.11); full matrix via tox.

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk
include $(ROOT_MAKE_DIR)/package/canon-api-package.mk

PACKAGE_IMPORT_NAME := bijux_canon_index
API_MODE := freeze
FMT_DIRS          := src tests
CODESPELL         := $(if $(ACT),$(ACT)/codespell,codespell) --ignore-words-list=ND,nd
API_LOG          = $(API_ARTIFACTS_DIR)/openapi_drift.log
API_DRIFT_COMMAND = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_index.api.v1:build_app --schema "$(API_SCHEMA_YAML)" --out "$(API_ARTIFACTS_DIR)/openapi.generated.json"
SECURITY_AUDIT_PREPARE_MODE := pyproject
PIP_AUDIT_INPUTS := -r "$(SECURITY_REQS)"
DOCS_DEV_ADDR := 0.0.0.0:8000
DOCS_EXTRA_CLEAN_PATHS := docs/site
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_index/core) $(abspath src/bijux_canon_index/contracts) $(abspath src/bijux_canon_index/domain)
BUILD_PRE_TARGETS := clean install fmt lint test quality security sbom
BUILD_POST_TARGETS := build-release-metadata
PUBLISH_DIST_DIR := $(PROJECT_ARTIFACTS_DIR)/release
PUBLISH_UPLOAD_ENABLED := 0
TEST_MAIN_ARGS := --maxfail=1
BUILD_DIR := $(PROJECT_ARTIFACTS_DIR)/release
PACKAGE_BOOTSTRAP_PREREQS := $(VENV)
PACKAGE_BOOTSTRAP_TARGETS := lint quality security api docs
PACKAGE_CLEAN_EXTRA_PATHS := $(COMMON_API_TEMP_CLEAN_PATHS) session.sqlite docs/site $(COMMON_CONFIG_CACHE_CLEAN_PATHS)
BUILD_SUCCESS_MESSAGE := [OK] Release artifacts ready under $(PROJECT_ARTIFACTS_DIR)/release
PACKAGE_VENV_CREATE_MESSAGE := [INFO] Creating virtualenv with '$$(which $(PYTHON))' ...
PACKAGE_INSTALL_MESSAGE := [INFO] Installing dependencies...
PACKAGE_CLEAN_MESSAGE := [INFO] Cleaning (.venv) ...
PACKAGE_CLEAN_SOFT_MESSAGE := [INFO] Cleaning (no .venv) ...
PACKAGE_ALL_TARGETS := clean install fmt lint test quality api security sbom
PACKAGE_ALL_MESSAGE := [OK] All targets completed

include $(ROOT_MAKE_DIR)/package/gates.mk

# Run independent checks in parallel
.NOTPARALLEL:

build-release-metadata:
	@echo "[INFO] Generating SBOM"
	@if ! command -v $(PIP_AUDIT) >/dev/null 2>&1; then \
	  echo "→ Installing pip-audit into $(VENV)"; \
	  $(UV) pip install --python "$(VENV_PYTHON)" --upgrade pip-audit >/dev/null; \
	fi
	@$(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output "$(PROJECT_ARTIFACTS_DIR)/release/sbom.json" || true
	@echo "[INFO] Refreshing pinned OpenAPI v1"
	@$(VENV_PYTHON) -c 'from pathlib import Path; import json; from bijux_canon_index.api.v1 import build_app; output = Path("$(API_DIR)/v1/pinned_openapi.json"); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(build_app().openapi(), indent=2, sort_keys=True), encoding="utf-8")'
	@cd "$(PROJECT_ARTIFACTS_DIR)/release" && shasum -a 256 *.whl *.tar.gz > SHA256SUMS
	@echo "[INFO] Release metadata refreshed"

release: build
	@echo "[OK] build target completed (alias for make release)"
.PHONY: build-release-metadata release
