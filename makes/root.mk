# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

include $(ROOT_MAKEFILE_DIR)/root/env.mk
include $(ROOT_MAKEFILE_DIR)/root/packages.mk

include $(ROOT_MAKEFILE_DIR)/root/dispatch.mk
include $(ROOT_MAKEFILE_DIR)/root/docs.mk
include $(ROOT_MAKEFILE_DIR)/bijux-py/standard.mk

DEFAULT_GOAL := help
.PHONY: \
	help list list-all install lock lock-check lint quality security test docs docs-check docs-serve api build sbom clean all \
	clean-root-artifacts root-check-env standard-bijux-py

ROOT_FORBIDDEN_ARTIFACTS ?= \
	"$(CURDIR)/.hypothesis" \
	"$(CURDIR)/.pytest_cache" \
	"$(CURDIR)/.ruff_cache" \
	"$(CURDIR)/.mypy_cache" \
	"$(CURDIR)/.coverage" \
	"$(CURDIR)/.coverage."* \
	"$(CURDIR)/.benchmarks" \
	"$(CURDIR)/htmlcov" \
	"$(CURDIR)/configs/.pytest_cache" \
	"$(CURDIR)/configs/.ruff_cache" \
	"$(CURDIR)/configs/.mypy_cache" \
	"$(CURDIR)/configs/.hypothesis"

$(ROOT_CHECK_STAMP): pyproject.toml uv.lock
	@mkdir -p "$(ROOT_ARTIFACTS_DIR)"
	@rm -rf "$(ROOT_CHECK_VENV)"
	@$(UV_SYNC)
	@touch "$(ROOT_CHECK_STAMP)"

list:
	@printf "%s\n" $(PRIMARY_PACKAGES)

list-all:
	@printf "%s\n" $(ALL_PACKAGES)

ROOT_INSTALL_PREREQS := root-check-env
ROOT_CHECK_ENV_PREREQS := pyproject.toml uv.lock $(ROOT_CHECK_STAMP)
ROOT_CLEAN_ROOT_ARTIFACTS_COMMAND := @rm -rf $(ROOT_FORBIDDEN_ARTIFACTS) || true
ROOT_ALL_TARGETS := test lint quality security docs api build sbom
ROOT_DEFINE_CLEAN := 0

include $(ROOT_MAKEFILE_DIR)/bijux-py/root-lifecycle.mk

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
