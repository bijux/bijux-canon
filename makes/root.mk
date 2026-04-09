ROOT_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

include $(ROOT_MAKEFILE_DIR)/bijux-py/root-env.mk
include $(ROOT_MAKEFILE_DIR)/env.mk
include $(ROOT_MAKEFILE_DIR)/packages.mk

ROOT_DEV_PYTHONPATH := $(CURDIR)/packages/bijux-canon-dev/src
ROOT_CHECK_VENV := $(ROOT_ARTIFACTS_DIR)/check-venv
ROOT_DOCS_DEV_ADDR ?= 127.0.0.1:8001
UV_SYNC := UV_PROJECT_ENVIRONMENT="$(ROOT_CHECK_VENV)" $(UV) sync --frozen --group dev --python "$(PYTHON)"

include $(ROOT_MAKEFILE_DIR)/bijux-py/repository-root.mk

include $(ROOT_MAKEFILE_DIR)/bijux-py/root-package-dispatch.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/root-docs.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/repository-make-layout.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/shared-bijux-py.mk

HELP_WIDTH := 26
include $(ROOT_MAKEFILE_DIR)/bijux-py/help.mk

##@ Repository
help: ## Show generated repository commands from included make modules
list: ## List primary package slugs
list-all: ## List every canonical package slug
install: ## Sync the shared root uv environment from pyproject.toml and uv.lock
lock: ## Refresh uv.lock from pyproject.toml
lock-check: ## Verify uv.lock matches pyproject.toml
all: ## Run the repository test, lint, quality, security, docs, api, build, and sbom flows
root-check-env: ## Create or refresh the shared root check environment
clean-root-artifacts: ## Remove stray root-level caches outside artifacts
check-shared-bijux-py: ## Verify shared bijux-py make modules match across sibling repositories
check-make-layout: ## Validate the repository make tree shape and required entrypoints
