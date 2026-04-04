# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

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

##@ Core
all-parallel: ## Run pipeline with parallelized lint, quality, security, and api
endif
