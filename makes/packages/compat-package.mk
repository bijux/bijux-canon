PACKAGE_KIND ?= python
COMPAT_MONOREPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
COMPAT_PROJECT_SLUG := $(notdir $(abspath $(CURDIR)))
COMPAT_CANONICAL_PACKAGE_DIR ?=

ifeq ($(COMPAT_PROJECT_SLUG),compat-agentic-flows)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-runtime
else ifeq ($(COMPAT_PROJECT_SLUG),compat-bijux-canon)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-runtime
else ifeq ($(COMPAT_PROJECT_SLUG),compat-bijux-agent)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-agent
else ifeq ($(COMPAT_PROJECT_SLUG),compat-bijux-rag)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-ingest
else ifeq ($(COMPAT_PROJECT_SLUG),compat-bijux-rar)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-reason
else ifeq ($(COMPAT_PROJECT_SLUG),compat-bijux-vex)
COMPAT_CANONICAL_PACKAGE_DIR := $(COMPAT_MONOREPO_ROOT)/packages/bijux-canon-index
endif

LINT_DIRS ?= src hatch_build.py
LINT_TARGETS ?= src hatch_build.py
MYPY_TARGETS ?= src hatch_build.py
CODESPELL_TARGETS ?= README.md hatch_build.py overview.md pyproject.toml
RADON_TARGETS ?= hatch_build.py
INTERROGATE_PATHS ?= src hatch_build.py
QUALITY_PATHS ?= src
QUALITY_VULTURE_MIN_CONFIDENCE ?= 80
SECURITY_PATHS ?= src hatch_build.py
PACKAGE_INSTALL_STAMP ?= $(PROJECT_ARTIFACTS_DIR)/.compat-toolchain.stamp
PACKAGE_INSTALL_EDITABLE ?= 0
PACKAGE_INSTALL_MESSAGE ?= → Installing compatibility package toolchain...
PACKAGE_INSTALL_PYTHON_PACKAGES ?= \
  pytest pytest-asyncio pytest-cov pytest-timeout \
  ruff mypy pydantic codespell vulture deptry interrogate bandit pip-audit \
  build twine hatchling hatch-vcs \
  $(COMPAT_CANONICAL_PACKAGE_DIR)
ENABLE_MYPY ?= 1
ENABLE_CODESPELL ?= 1
ENABLE_RADON ?= 0
ENABLE_PYDOCSTYLE ?= 0
SKIP_DEPTRY ?= 0
SKIP_INTERROGATE ?= 0
SKIP_MYPY ?= 0
SKIP_BANDIT ?= 0
TEST_SOURCE_PATHS ?= src $(COMPAT_CANONICAL_PACKAGE_DIR)/src
TEST_COVERAGE_SOURCE ?= src
TEST_MAIN_ARGS ?= -m "not slow"
PUBLISH_PACKAGE_NAME ?= $(patsubst compat-%,%,$(PROJECT_SLUG))
PUBLISH_UPLOAD_ENABLED ?= 0
PACKAGE_DEFINE_BOOTSTRAP ?= 0
PACKAGE_CLEAN_PATHS ?= \
  $(COMMON_ARTIFACT_CLEAN_PATHS) $(COMMON_BUILD_CLEAN_PATHS) "$(PACKAGE_INSTALL_STAMP)"
PACKAGE_INSTALL_TARGETS ?= \
  test test-unit test-ci \
  lint-artifacts quality security-bandit security-audit security-deps \
  build publish publish-test release-dry
LINT_PRE_TARGETS += compat-sync-canonical
TEST_PRE_TARGETS += compat-sync-canonical

test-all: TEST_MAIN_ARGS =
test-all: PYTEST_ADDOPTS_EXTRA = -o timeout=0
test-all: test
.PHONY: test-all

test-all-plus-run-time: TEST_MAIN_ARGS =
test-all-plus-run-time: PYTEST_ADDOPTS_EXTRA = -o timeout=0 --durations=0 --durations-min=0
test-all-plus-run-time: test
.PHONY: test-all-plus-run-time

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

compat-sync-canonical: | $(VENV)
	@set -e; \
	if [ -z "$(strip $(COMPAT_CANONICAL_PACKAGE_DIR))" ]; then \
	  echo "✖ COMPAT_CANONICAL_PACKAGE_DIR is required for $(PROJECT_SLUG)"; \
	  exit 1; \
	fi; \
	if ! $(UV) pip install --python "$(VENV_PYTHON)" --editable "$(COMPAT_CANONICAL_PACKAGE_DIR)"; then \
	  echo "→ uv pip install failed; retrying with python -m pip"; \
	  "$(VENV_PYTHON)" -m pip install --editable "$(COMPAT_CANONICAL_PACKAGE_DIR)"; \
	fi
.PHONY: compat-sync-canonical

##@ Core
clean: ## Remove virtualenv plus compatibility package artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install compatibility package toolchain
help: ## Show this help
