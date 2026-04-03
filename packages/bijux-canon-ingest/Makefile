# SPDX-License-Identifier: Apache-2.0

PROJECT_SLUG := bijux-canon-ingest

include ../../makes/shared/python-package.mk

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX     := $(PROJECT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME          := $(PROJECT_ARTIFACTS_DIR)/xdg_cache
export COVERAGE_FILE           := $(PROJECT_ARTIFACTS_DIR)/test/.coverage
LINT_DIRS                      := src/bijux_canon_ingest tests
MYPY_TARGETS                   = $(if $(LINT_SCOPE),$(LINT_SCOPE),src/bijux_canon_ingest)
MYPY_FLAGS                     := --ignore-missing-imports --follow-imports normal --warn-redundant-casts --strict-optional --namespace-packages --check-untyped-defs --disallow-incomplete-defs --disallow-untyped-defs --no-implicit-optional --warn-return-any
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
API_DRIFT_COMMAND              = $(VENV_PYTHON) "$(MONOREPO_ROOT)/scripts/bijux-canon-ingest/openapi_drift.py" --schema "$(API_SCHEMA)" --out "$(API_DRIFT_OUT)"
BUILD_CHECK_DISTS              := 1
BUILD_CLEAN_PATHS              := dist build *.egg-info
PUBLISH_UPLOAD_ENABLED         := 0

.NOTPARALLEL: all clean

include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/docs.mk
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/sbom.mk
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
	@echo "→ Cleaning ($(VENV)) ..."
	@$(RM) $(VENV)

clean-soft:
	@echo "→ Cleaning (artifacts, caches) ..."
	@$(RM) \
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox .nox \
	  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
	  artifacts "$(PROJECT_ARTIFACTS_DIR)" site .cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

# Ensure core tasks run inside the managed virtualenv
test lint fmt quality security api docs build sbom: install

# Pipelines
all: clean install test lint quality security api docs build sbom
	@echo "✔ All targets completed"

help:
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^##@/ {gsub(/^##@ */,""); print "\n\033[1m" $$0 "\033[0m"; next} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
.PHONY: help

##@ Core
clean: ## Remove virtualenv plus caches/artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run clean → install → test → lint
help: ## Show this help
