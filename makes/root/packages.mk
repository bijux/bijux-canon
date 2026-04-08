# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_PACKAGE_PROFILE_DIR ?= $(ROOT_MAKEFILE_DIR)/packages
PACKAGE_MAKE_DIR ?= $(ROOT_PACKAGE_PROFILE_DIR)

PRIMARY_PACKAGES := \
	bijux-canon-dev \
	bijux-canon-runtime \
	bijux-canon-agent \
	bijux-canon-ingest \
	bijux-canon-reason \
	bijux-canon-index

COMPAT_PACKAGES := \
	compat-agentic-flows \
	compat-bijux-agent \
	compat-bijux-rag \
	compat-bijux-rar \
	compat-bijux-vex

ALL_PACKAGES := $(PRIMARY_PACKAGES) $(COMPAT_PACKAGES)
CHECK_PACKAGES := $(ALL_PACKAGES)
PACKAGE ?=

PACKAGE_ALIASES := \
	agentic-flows=bijux-canon-runtime \
	bijux-agent=bijux-canon-agent \
	bijux-rag=bijux-canon-ingest \
	bijux-rar=bijux-canon-reason \
	bijux-vex=bijux-canon-index

PACKAGE_GROUPS_bijux-canon-dev := primary check buildable sbom test api_profile_off
PACKAGE_GROUPS_bijux-canon-runtime := primary check buildable sbom test api
PACKAGE_GROUPS_bijux-canon-agent := primary check buildable sbom test api
PACKAGE_GROUPS_bijux-canon-ingest := primary check buildable sbom test api
PACKAGE_GROUPS_bijux-canon-reason := primary check buildable sbom test api
PACKAGE_GROUPS_bijux-canon-index := primary check buildable sbom test api
PACKAGE_GROUPS_compat-agentic-flows := compat check
PACKAGE_GROUPS_compat-bijux-agent := compat check
PACKAGE_GROUPS_compat-bijux-rag := compat check
PACKAGE_GROUPS_compat-bijux-rar := compat check
PACKAGE_GROUPS_compat-bijux-vex := compat check

PACKAGE_PROFILE_bijux-canon-dev := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-dev.mk
PACKAGE_PROFILE_bijux-canon-runtime := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-runtime.mk
PACKAGE_PROFILE_bijux-canon-agent := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-agent.mk
PACKAGE_PROFILE_bijux-canon-ingest := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-ingest.mk
PACKAGE_PROFILE_bijux-canon-reason := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-reason.mk
PACKAGE_PROFILE_bijux-canon-index := $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-index.mk
PACKAGE_PROFILE_compat-agentic-flows := $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk
PACKAGE_PROFILE_compat-bijux-agent := $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk
PACKAGE_PROFILE_compat-bijux-rag := $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk
PACKAGE_PROFILE_compat-bijux-rar := $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk
PACKAGE_PROFILE_compat-bijux-vex := $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk

ROOT_PACKAGE_TARGETS := test lint quality security api build sbom clean
ROOT_TARGET_GROUPS_test := test
ROOT_TARGET_GROUPS_lint := check
ROOT_TARGET_GROUPS_quality := check
ROOT_TARGET_GROUPS_security := check
ROOT_TARGET_GROUPS_api := api
ROOT_TARGET_GROUPS_build := buildable
ROOT_TARGET_GROUPS_sbom := sbom
ROOT_TARGET_GROUPS_clean := primary compat
ROOT_TARGET_SHARED_ENV_test := 0
ROOT_TARGET_SHARED_ENV_lint := 1
ROOT_TARGET_SHARED_ENV_quality := 1
ROOT_TARGET_SHARED_ENV_security := 1
ROOT_TARGET_SHARED_ENV_api := 0
ROOT_TARGET_SHARED_ENV_build := 0
ROOT_TARGET_SHARED_ENV_sbom := 0
ROOT_TARGET_SHARED_ENV_clean := 0
ROOT_TARGET_POST_clean = @$(MAKE) clean-root-artifacts

VALID_PACKAGE_VALUES := $(ALL_PACKAGES) $(foreach mapping,$(PACKAGE_ALIASES),$(word 1,$(subst =, ,$(mapping))))

ROOT_PACKAGE_DIRS := $(addprefix $(CURDIR)/packages/,$(ALL_PACKAGES))
ROOT_DISCOVERED_PACKAGE_DIRS := $(sort $(wildcard $(CURDIR)/packages/*))
ROOT_DECLARED_PACKAGE_PROFILE_FILES := $(foreach package,$(ALL_PACKAGES),$(PACKAGE_PROFILE_$(package)))
ROOT_MISSING_PACKAGE_DIRS := $(filter-out $(ROOT_DISCOVERED_PACKAGE_DIRS),$(ROOT_PACKAGE_DIRS))
ROOT_MISSING_PACKAGE_PROFILE_FILES := $(foreach file,$(ROOT_DECLARED_PACKAGE_PROFILE_FILES),$(if $(wildcard $(file)),,$(file)))
ROOT_UNDECLARED_PACKAGE_DIRS := $(filter-out $(ROOT_PACKAGE_DIRS),$(ROOT_DISCOVERED_PACKAGE_DIRS))

ifneq ($(strip $(ROOT_MISSING_PACKAGE_DIRS)),)
$(error Package inventory references missing directories: $(ROOT_MISSING_PACKAGE_DIRS))
endif

ifneq ($(strip $(ROOT_MISSING_PACKAGE_PROFILE_FILES)),)
$(error Package inventory references missing profiles: $(ROOT_MISSING_PACKAGE_PROFILE_FILES))
endif

ifneq ($(strip $(ROOT_UNDECLARED_PACKAGE_DIRS)),)
$(error Package directories are missing from makes/root/packages.mk: $(notdir $(ROOT_UNDECLARED_PACKAGE_DIRS)))
endif

define resolve_package
$(strip \
$(if $(filter $(1),$(ALL_PACKAGES)),$(1), \
$(foreach mapping,$(PACKAGE_ALIASES), \
$(if $(filter $(1),$(word 1,$(subst =, ,$(mapping)))),$(word 2,$(subst =, ,$(mapping)))))))
endef

define resolve_package_profile
$(strip $(or $(PACKAGE_PROFILE_$(1)),$(PACKAGE_MAKE_DIR)/$(1).mk))
endef

define assert_package
	@if [ -n "$(PACKAGE)" ] && [ -z "$(call resolve_package,$(PACKAGE))" ]; then \
	  echo "Unknown package '$(PACKAGE)'."; \
	  echo "Valid package values:"; \
	  printf "  %s\n" $(VALID_PACKAGE_VALUES); \
	  exit 2; \
	fi
endef

define packages_in_group
$(strip $(foreach package,$(ALL_PACKAGES),$(if $(filter $(1),$(PACKAGE_GROUPS_$(package))),$(package))))
endef

$(foreach target,$(ROOT_PACKAGE_TARGETS),$(eval ROOT_TARGET_PACKAGES_$(target) := $(call packages_in_group,$(ROOT_TARGET_GROUPS_$(target)))))
PACKAGE_PROFILE_MAPPINGS := $(foreach package,$(ALL_PACKAGES),$(package)=$(call resolve_package_profile,$(package)))
