# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

PROJECT_SLUG := bijux-agent

include ../../makes/shared/python-package.mk

.NOTPARALLEL: all clean

# Modular Includes
include $(MAKE_DIR)/api.mk
include $(MAKE_DIR)/build.mk
include $(MAKE_DIR)/docs.mk
include $(MAKE_DIR)/lint.mk
include $(MAKE_DIR)/quality.mk
include $(MAKE_DIR)/sbom.mk
include $(MAKE_DIR)/security.mk
include $(MAKE_DIR)/test.mk
include $(MAKE_DIR)/publish.mk

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
	  .ruff_cache .mypy_cache .pytype .hypothesis .coverage.* .coverage .benchmarks \
	  spec.json openapitools.json node_modules site \
	  docs/reference artifacts "$(PROJECT_ARTIFACTS_DIR)" usage_test usage_test_artifacts .cache || true
	@$(RM) $(CONFIG_DIR)/.ruff_cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
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

ci-fast: lint test mypy-core
.PHONY: ci-fast

line_limit:
	@$(VENV_PYTHON) "$(MONOREPO_ROOT)/scripts/bijux-agent/check_line_limit.py"
.PHONY: line_limit

# Utilities
define run_tool
	printf "→ %s %s\n" "$(1)" "$$file"; \
	OUT=`$(2) "$$file" 2>&1`; \
	if [ $$? -eq 0 ]; then \
		printf "  ✔ %s OK\n" "$(1)"; \
	else \
		printf "  ✘ %s failed:\n" "$(1)"; \
		printf "%s\n" "$$OUT" | head -10; \
	fi
endef

define read_pyproject_version
$(strip $(shell \
  python3 -c 'import tomllib; \
  print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])' \
  2>/dev/null || echo 0.0.0 \
))
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
all: ## Run full pipeline (clean → sbom)
all-parallel: ## Run pipeline with parallelized lint, quality, security, api, and docs
help: ## Show this help
