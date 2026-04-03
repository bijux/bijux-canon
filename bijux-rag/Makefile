# SPDX-License-Identifier: MIT

PROJECT_SLUG := bijux-rag

include ../makes/shared/python-package.mk

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX     := artifacts/pycache
export XDG_CACHE_HOME          := artifacts/xdg_cache
export COVERAGE_FILE           := artifacts/test/.coverage

.NOTPARALLEL: all clean

include $(MAKE_DIR)/test.mk
include $(MAKE_DIR)/lint.mk
include $(MAKE_DIR)/docs.mk
include $(MAKE_DIR)/api.mk
include $(MAKE_DIR)/build.mk
include $(MAKE_DIR)/quality.mk
include $(MAKE_DIR)/security.mk
include $(MAKE_DIR)/sbom.mk
include $(MAKE_DIR)/citation.mk
include $(MAKE_DIR)/publish.mk
include $(MAKE_DIR)/hygiene.mk

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
	  .ruff_cache .mypy_cache .pytype .hypothesis .coverage.* .coverage .benchmarks \
	  artifacts site .cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi

# Ensure core tasks run inside the managed virtualenv
test lint fmt type quality security api docs build sbom citation hygiene: install

# Pipelines
all: clean install test lint quality security api docs build sbom citation hygiene
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
