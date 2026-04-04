# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

include $(ROOT_MAKEFILE_DIR)/root/env.mk
include $(ROOT_MAKEFILE_DIR)/root/packages.mk
include $(ROOT_MAKEFILE_DIR)/root/targets.mk

include $(ROOT_MAKEFILE_DIR)/root/dispatch.mk
include $(ROOT_MAKEFILE_DIR)/root/toolchain.mk
include $(ROOT_MAKEFILE_DIR)/root/cleanup.mk
include $(ROOT_MAKEFILE_DIR)/root/docs.mk

DEFAULT_GOAL := help
.PHONY: \
	help list list-all lint quality security test docs docs-check docs-serve api build sbom clean all \
	clean-root-artifacts root-check-env

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
all: ## Run the repository test, lint, quality, security, docs, api, build, and sbom flows
