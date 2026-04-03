# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# Testing policy: gates (lint/quality/security/typing) intentionally run on lowest supported Python (3.11); full matrix via tox.

# Core Config
.DELETE_ON_ERROR:
.DEFAULT_GOAL         := all
.SHELLFLAGS           := -eu -o pipefail -c
SHELL                 := bash
PYTHON                := python3
VENV                  := .venv
VENV_PYTHON           := $(VENV)/bin/python
ACT                   := $(VENV)/bin
RM                    := rm -rf

.NOTPARALLEL: all clean

# Modular Includes
include makefiles/fmt.mk
include makefiles/lint.mk
include makefiles/test.mk
include makefiles/docs.mk
include makefiles/api.mk
include makefiles/hygiene.mk
include makefiles/security.mk
include makefiles/sbom.mk
include makefiles/quality.mk
include makefiles/freeze.mk
include makefiles/citation.mk

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
	  docs/site artifacts || true
	@$(RM) config/.ruff_cache || true
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
	@mkdir -p artifacts/release
	@$(VENV_PYTHON) -m build --wheel --sdist --outdir artifacts/release
	@echo "[INFO] Generating SBOM"
	@if ! command -v $(PIP_AUDIT) >/dev/null 2>&1; then \
	  echo "→ Installing pip-audit into $(VENV)"; \
	  $(VENV_PYTHON) -m pip install --upgrade pip-audit >/dev/null; \
	fi
	@$(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output artifacts/release/sbom.json || true
	@echo "[INFO] Refreshing OpenAPI v1"
	@$(VENV_PYTHON) - <<'PY'\nfrom pathlib import Path\nimport json\nfrom bijux_vex.api.v1 import build_app\nPath('api/v1').mkdir(parents=True, exist_ok=True)\nPath('api/v1/openapi.v1.json').write_text(json.dumps(build_app().openapi(), indent=2))\nPY
	@cd artifacts/release && shasum -a 256 *.whl *.tar.gz > SHA256SUMS
	@echo "[OK] Release artifacts ready under artifacts/release"

build: release
	@echo "[OK] build target completed (alias for make release)"

# Utilities
define run_tool
	printf "[INFO] %s %s\n" "$(1)" "$$file"; \
	OUT=`$(2) "$$file" 2>&1`; \
	if [ $$? -eq 0 ]; then \
		printf "  [OK] %s\n" "$(1)"; \
	else \
		printf "  [ERR] %s failed:\n" "$(1)"; \
		printf "%s\n" "$$OUT" | head -10; \
	fi
endef

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
