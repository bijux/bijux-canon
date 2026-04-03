# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
PACKAGE_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PROJECT_SLUG := bijux-canon-dev

include $(PACKAGE_MAKEFILE_DIR)/../shared/python-package.mk

.NOTPARALLEL: all clean

LINT_DIRS         := src/bijux_canon_dev tests
INTERROGATE_PATHS := src/bijux_canon_dev
QUALITY_PATHS     := src/bijux_canon_dev
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_canon_dev
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SKIP_MYPY         := 1
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
PUBLISH_UPLOAD_ENABLED := 0
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := build dist *.egg-info

include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/publish.mk

$(VENV):
	@echo "→ Creating virtualenv with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv "$(VENV)"

install: $(VENV)
	@echo "→ Installing dependencies..."
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(VENV_PYTHON) -m pip install -e ".[dev]"

bootstrap: install
.PHONY: bootstrap

clean: clean-soft
	@echo "→ Cleaning ($(VENV)) ..."
	@$(RM) "$(VENV)"

clean-soft:
	@echo "→ Cleaning (artifacts, caches) ..."
	@$(RM) \
	  .pytest_cache htmlcov coverage.xml dist build *.egg-info .tox .nox \
	  .ruff_cache .mypy_cache .hypothesis .coverage.* .coverage .benchmarks \
	  artifacts "$(PROJECT_ARTIFACTS_DIR)" .cache || true
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	  find . -type f -name '*.pyc' -delete; \
	fi

all: clean install test lint quality security build sbom
	@echo "✔ All targets completed"

help:
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^##@/ {gsub(/^##@ */,""); print "\n\033[1m" $$0 "\033[0m"; next} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
.PHONY: help

##@ Core
clean: ## Remove virtualenv plus caches and artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run clean → install → test → lint
help: ## Show this help
