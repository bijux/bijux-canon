# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/api.mk
include $(ROOT_MAKE_DIR)/publish.mk

PACKAGE_DEFINE_ALL_PARALLEL ?= 0
PACKAGE_ALL_PARALLEL_PRE_TARGETS ?= clean install
PACKAGE_ALL_PARALLEL_MAIN_TARGETS ?= quality security api
PACKAGE_ALL_PARALLEL_MAIN_JOBS ?= 4
PACKAGE_ALL_PARALLEL_FINAL_TARGETS ?= build sbom
PACKAGE_ALL_PARALLEL_MESSAGE ?= ✔ All targets completed (parallel mode)

ifeq ($(PACKAGE_DEFINE_ALL_PARALLEL),1)
all-parallel: $(PACKAGE_ALL_PARALLEL_PRE_TARGETS)
	@$(SELF_MAKE) -j$(PACKAGE_ALL_PARALLEL_MAIN_JOBS) $(PACKAGE_ALL_PARALLEL_MAIN_TARGETS)
	@$(SELF_MAKE) $(PACKAGE_ALL_PARALLEL_FINAL_TARGETS)
	@echo "$(PACKAGE_ALL_PARALLEL_MESSAGE)"
.PHONY: all-parallel
endif

##@ Core
clean: ## Remove virtualenv plus package artifacts
clean-soft: ## Remove build artifacts but keep the virtualenv
install: ## Install package dependencies into the virtualenv
help: ## Show package commands
bootstrap: ## Install package prerequisites for gate targets
all-parallel: ## Run parallel package checks when enabled
