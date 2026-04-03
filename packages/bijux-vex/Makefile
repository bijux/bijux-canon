# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# Testing policy: gates (lint/quality/security/typing) intentionally run on lowest supported Python (3.11); full matrix via tox.

PROJECT_SLUG := bijux-vex

include ../../makes/shared/python-package.mk

.NOTPARALLEL: all clean

LINT_DIRS         := src/bijux_vex
FMT_DIRS          := src tests scripts/bijux-vex
ENABLE_MYPY       := 0
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 1
ENABLE_PYDOCSTYLE := 0
ENABLE_PYTYPE     := 0
RUFF_CHECK_FIX    := 1
INTERROGATE_PATHS := src/bijux_vex
QUALITY_PATHS     := src/bijux_vex
QUALITY_PRE_TARGETS := hygiene
QUALITY_VULTURE_MIN_CONFIDENCE := 80
QUALITY_CLEAN_SITE := 1
SECURITY_PATHS    := src/bijux_vex
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SECURITY_AUDIT_PREPARE_MODE := pyproject
PIP_AUDIT_INPUTS = -r "$(SECURITY_REQS)"
DOCS_DEV_ADDR    := 0.0.0.0:8000
DOCS_EXTRA_CLEAN_PATHS := site docs/site
PUBLISH_DIST_DIR := $(PROJECT_ARTIFACTS_DIR)/release
PUBLISH_UPLOAD_ENABLED := 0

# Modular Includes
include $(ROOT_MAKE_DIR)/lint.mk
include $(MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/docs.mk
include $(MAKE_DIR)/api.mk
include $(MAKE_DIR)/hygiene.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(MAKE_DIR)/freeze.mk
include $(ROOT_MAKE_DIR)/publish.mk

# Environment
$(VENV):
	@echo "[INFO] Creating virtualenv with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv $(VENV)

install: $(VENV)
	@echo "[INFO] Installing dependencies..."
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(VENV_PYTHON) -m pip install -e ".[dev]"

bootstrap: $(VENV)
.PHONY: bootstrap

# Cleanup
clean:
	@$(MAKE) clean-soft
	@echo "[INFO] Cleaning (.venv) ..."
	@$(RM) $(VENV)

clean-soft:
	@echo "[INFO] Cleaning (no .venv) ..."
	@$(RM) \
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox \
	  .ruff_cache .mypy_cache .pytype .hypothesis .coverage.* .coverage .benchmarks \
	  spec.json openapitools.json node_modules session.sqlite site \
	  docs/site artifacts "$(PROJECT_ARTIFACTS_DIR)" || true
	@$(RM) $(CONFIG_DIR)/.ruff_cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	  find . -type f -name '*.pyc' -delete; \
	fi

# Pipelines
all: clean install fmt lint test quality docs api hygiene security sbom
	@echo "[OK] All targets completed"

# Run independent checks in parallel
lint quality security api docs: | bootstrap
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
	@echo "[INFO] Refreshing OpenAPI v1"
	@$(VENV_PYTHON) - <<'PY'\nfrom pathlib import Path\nimport json\nfrom bijux_vex.api.v1 import build_app\nPath('$(API_DIR)/v1').mkdir(parents=True, exist_ok=True)\nPath('$(API_DIR)/v1/openapi.v1.json').write_text(json.dumps(build_app().openapi(), indent=2))\nPY
	@cd "$(PROJECT_ARTIFACTS_DIR)/release" && shasum -a 256 *.whl *.tar.gz > SHA256SUMS
	@echo "[OK] Release artifacts ready under $(PROJECT_ARTIFACTS_DIR)/release"

build: release
	@echo "[OK] build target completed (alias for make release)"

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
all: ## Run full pipeline
help: ## Show this help
