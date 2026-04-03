# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

PROJECT_SLUG := agentic-flows
PYTHON := python3.11

include ../makes/shared/python-package.mk

.NOTPARALLEL: all clean

# ---- Single virtualenv (Python 3.11+) ----
ACT             := $(if $(wildcard $(VENV)/bin/activate),$(VENV)/bin,$(ACT))

# ---- Includes ----
include $(MAKE_DIR)/test.mk
include $(MAKE_DIR)/lint.mk
include $(MAKE_DIR)/quality.mk
include $(MAKE_DIR)/security.mk
include $(MAKE_DIR)/build.mk
include $(MAKE_DIR)/sbom.mk
include $(MAKE_DIR)/docs.mk
include $(MAKE_DIR)/api.mk
include $(MAKE_DIR)/citation.mk
include $(MAKE_DIR)/dictionary.mk
include $(MAKE_DIR)/changelog.mk
include $(MAKE_DIR)/architecture.mk

-include .env
export

.PHONY: install ensure-venv nlenv \
        clean clean-soft clean-venv \
        manage_examples manage_models \
        all help

$(VENV):
	@echo "→ Creating virtualenv at '$(VENV)' with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv "$(VENV)"

ensure-venv: $(VENV) ## Ensure venv exists and deps are installed
	@set -e; \
	echo "→ Ensuring dependencies in $(VENV) ..."; \
	PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	"$(VENV_PYTHON)" -m pip install --upgrade pip setuptools wheel; \
	EXTRAS="$${EXTRAS:-dev}"; \
	if [ -n "$$EXTRAS" ]; then SPEC=".[$$EXTRAS]"; else SPEC="."; fi; \
	echo "→ Installing: $$SPEC"; \
	PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
	"$(VENV_PYTHON)" -m pip install -e "$$SPEC"

install: ensure-venv ## Install project into .venv (dev)
	@true

nlenv: ## Print activate command
	@echo "Run: source $(ACT)/activate"

clean-soft: ## Remove build artifacts but keep venv
	@echo "→ Cleaning (no .venv removal) ..."
	@$(RM) \
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox demo .tmp_home \
	  .ruff_cache .mypy_cache .pytype .hypothesis .coverage.* .coverage .benchmarks \
	  artifacts .cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

clean-venv:
	@echo "→ Cleaning ($(VENV)) ..."
	@$(RM) "$(VENV)"

clean: clean-soft clean-venv ## Remove venv + artifacts

all: clean install test lint quality security sbom build docs api citation dictionary ## Full pipeline
	@echo "✔ All targets completed"

manage_examples:
	"$(VENV_PYTHON)" scripts/manage_examples.py

manage_models:
	"$(VENV_PYTHON)" scripts/manage_models.py

help: ## Show this help
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
