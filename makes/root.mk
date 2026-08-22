ROOT_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# Build backends may change directories, so every inherited process/cache path
# must derive from an absolute repository artifact root.
PROJECT_ARTIFACTS_DIR := $(abspath artifacts)
PROJECT_PROCESS_DIR := $(abspath artifacts/root/process)

include $(ROOT_MAKEFILE_DIR)/bijux-py/root/env.mk
include $(ROOT_MAKEFILE_DIR)/env.mk
include $(ROOT_MAKEFILE_DIR)/packages.mk

ROOT_DEV_PYTHONPATH := $(CURDIR)/packages/bijux-canon-dev/src
ROOT_CHECK_VENV := $(ROOT_ARTIFACTS_DIR)/check-venv
ROOT_DOCS_DEV_ADDR ?= 127.0.0.1:8001
UV_SYNC := UV_PROJECT_ENVIRONMENT="$(ROOT_CHECK_VENV)" $(UV) sync --frozen --group dev --python "$(PYTHON)"
BIJUX_PY_SYSTEM_REL ?= .bijux/shared/bijux-makes-py
BIJUX_GH_PY_SHARED_DIR ?= .bijux/shared/bijux-gh
ROOT_PACKAGE_TARGETS += test-all test-all-plus-run-time coverage-core
ROOT_TARGET_GROUPS_test-all ?= check
ROOT_TARGET_GROUPS_test-all-plus-run-time ?= check
ROOT_TARGET_GROUPS_coverage-core ?= primary
ROOT_TARGET_SHARED_ENV_test-all ?= 1
ROOT_TARGET_SHARED_ENV_test-all-plus-run-time ?= 1
ROOT_TARGET_SHARED_ENV_coverage-core ?= 1
ROOT_VULTURE_ARTIFACTS_DIR := $(PROJECT_ARTIFACTS_DIR)/root/quality
ROOT_VULTURE_LOG := $(ROOT_VULTURE_ARTIFACTS_DIR)/vulture.log
ROOT_VULTURE_PATHS := $(wildcard packages/*/src)
ROOT_VULTURE_WHITELIST := configs/vulture_whitelist.py
# Guard against stale local stamp state so root docs and helper lanes can
# recreate the shared check environment when the interpreter path was removed.
ROOT_CHECK_ENV_COMMAND = @test -x "$(ROOT_CHECK_PYTHON)" || { \
	echo "→ Rebuilding missing root check environment"; \
	rm -f "$(ROOT_CHECK_STAMP)"; \
	$(MAKE) "$(ROOT_CHECK_STAMP)"; \
}

include $(ROOT_MAKEFILE_DIR)/bijux-py/repository/root.mk

.PHONY: quality-dead-code

quality: quality-dead-code

quality-dead-code: root-check-env
	@echo "→ Running fatal repository dead-code analysis"
	@mkdir -p "$(ROOT_VULTURE_ARTIFACTS_DIR)"
	@set -eu; \
	  if ! "$(ROOT_CHECK_PYTHON)" -m vulture $(ROOT_VULTURE_PATHS) \
	    "$(ROOT_VULTURE_WHITELIST)" --min-confidence 100 \
	    >"$(ROOT_VULTURE_LOG)" 2>&1; then \
	    cat "$(ROOT_VULTURE_LOG)"; \
	    exit 1; \
	  fi
	@echo "✔ Fatal dead-code analysis passed"

include $(ROOT_MAKEFILE_DIR)/bijux-py/root/package-dispatch.mk
# Root verification must inspect the submitted tree. Package profiles may keep
# autofix defaults for their explicit formatting workflow, but never for lint.
lint: export RUFF_CHECK_FIX := 0
lint: export FMT_RUN_RUFF_CHECK_FIX := 0
ROOT_TARGET_PACKAGES_test-all := $(CHECK_PACKAGES)
ROOT_TARGET_PACKAGES_test-all-plus-run-time := $(CHECK_PACKAGES)
include $(ROOT_MAKEFILE_DIR)/bijux-py/root/docs.mk
include $(ROOT_MAKEFILE_DIR)/bijux-docs.mk
include $(ROOT_MAKEFILE_DIR)/bijux-std.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/repository/config-layout.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/repository/make-layout.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/bijux.mk

DOCS_BUILD_PREPARE_TARGETS := bijux-docs-sync docs-prepare-source
DOCS_CHECK_PREPARE_TARGETS := bijux-docs-sync docs-prepare-source
DOCS_SERVE_PREPARE_TARGETS := bijux-docs-sync docs-render-serve-config

HELP_WIDTH := 26
include $(ROOT_MAKEFILE_DIR)/bijux-py/ci/help.mk

##@ Repository
help: ## Show generated repository commands from included make modules
check: lock-check lint test quality security docs api build sbom ## Run the full repository verification flow
test-all: ## Run every repository test surface, including slow, evaluation, and real-local tests
test-all-plus-run-time: ## Run every repository test surface and report per-test durations
coverage-core: ## Enforce measured canonical-package coverage floors
list: ## List primary package slugs
list-all: ## List every canonical package slug
install: ## Sync the shared root uv environment from pyproject.toml and uv.lock
lock: ## Refresh uv.lock from pyproject.toml
lock-check: ## Verify uv.lock matches pyproject.toml
all: ## Run the repository test, lint, quality, security, docs, api, build, and sbom flows
root-check-env: ## Create or refresh the shared root check environment
clean-root-artifacts: ## Remove stray root-level caches outside artifacts
check-shared-bijux-py: ## Verify shared bijux-py make modules match across sibling repositories
check-config-layout: ## Validate the repository config tree shape and required tool configs
check-make-layout: ## Validate the repository make tree shape and required entrypoints
sync-badges: root-check-env ## Render shared badge blocks from docs/badges.md into README surfaces
	@"$(ROOT_CHECK_PYTHON)" -m bijux_canon_dev.docs.badge_sync sync
check-badges: root-check-env ## Verify README badge blocks match docs/badges.md
	@"$(ROOT_CHECK_PYTHON)" -m bijux_canon_dev.docs.badge_sync check
