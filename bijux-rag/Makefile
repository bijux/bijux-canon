# SPDX-License-Identifier: MIT

.DELETE_ON_ERROR:
.DEFAULT_GOAL         := all
.SHELLFLAGS           := -eu -o pipefail -c
SHELL                 := bash
PYTHON                := python3
VENV                  := .venv
VENV_PYTHON           := $(VENV)/bin/python
ACT                   := $(VENV)/bin
RM                    := rm -rf

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX     := artifacts/pycache
export XDG_CACHE_HOME          := artifacts/xdg_cache
export COVERAGE_FILE           := artifacts/test/.coverage

.NOTPARALLEL: all clean

include makefiles/test.mk
include makefiles/lint.mk
include makefiles/docs.mk
include makefiles/api.mk
include makefiles/build.mk
include makefiles/quality.mk
include makefiles/security.mk
include makefiles/sbom.mk
include makefiles/citation.mk
include makefiles/publish.mk
include makefiles/hygiene.mk

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
