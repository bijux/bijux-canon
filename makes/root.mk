# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

include $(ROOT_MAKEFILE_DIR)/root/env.mk
include $(ROOT_MAKEFILE_DIR)/root/packages.mk

include $(ROOT_MAKEFILE_DIR)/root/dispatch.mk
include $(ROOT_MAKEFILE_DIR)/root/toolchain.mk
include $(ROOT_MAKEFILE_DIR)/root/cleanup.mk
include $(ROOT_MAKEFILE_DIR)/root/docs.mk

DEFAULT_GOAL := help
.PHONY: \
	help list list-all install lock lock-check lint quality security test docs docs-check docs-serve api build sbom clean all \
	clean-root-artifacts root-check-env

install: root-check-env

lock:
	@$(UV) lock --python "$(PYTHON)"

lock-check:
	@$(UV) lock --check --python "$(PYTHON)"

list:
	@printf "%s\n" $(PRIMARY_PACKAGES)

list-all:
	@printf "%s\n" $(ALL_PACKAGES)

all: test lint quality security docs api build sbom

HELP_WIDTH := 26
include $(ROOT_MAKEFILE_DIR)/help.mk

##@ Repository
help: ## Show generated repository commands from included make modules
list: ## List primary package slugs
list-all: ## List every canonical package slug
install: ## Sync the shared root uv environment from pyproject.toml and uv.lock
lock: ## Refresh uv.lock from pyproject.toml
lock-check: ## Verify uv.lock matches pyproject.toml
all: ## Run the repository test, lint, quality, security, docs, api, build, and sbom flows
