# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_PACKAGE_PROFILE_DIR ?= $(ROOT_MAKEFILE_DIR)/packages
ROOT_PACKAGE_PROFILE_FILES := $(wildcard $(ROOT_PACKAGE_PROFILE_DIR)/*.mk)
ROOT_DECLARED_PACKAGE_FILES := \
	$(addprefix $(ROOT_PACKAGE_PROFILE_DIR)/,$(addsuffix .mk,$(PRIMARY_PACKAGES) $(COMPAT_PACKAGES)))
ROOT_DISCOVERED_PRIMARY_PACKAGES := $(basename $(notdir $(filter $(ROOT_PACKAGE_PROFILE_DIR)/bijux-canon-%.mk,$(ROOT_PACKAGE_PROFILE_FILES))))
ROOT_DISCOVERED_COMPAT_PACKAGES := $(basename $(notdir $(filter-out $(ROOT_PACKAGE_PROFILE_DIR)/compat-package.mk,$(filter $(ROOT_PACKAGE_PROFILE_DIR)/compat-%.mk,$(ROOT_PACKAGE_PROFILE_FILES)))))

include $(ROOT_MAKEFILE_DIR)/root/package-manifest.mk

ALL_PACKAGES := $(PRIMARY_PACKAGES) $(COMPAT_PACKAGES)
CHECK_PACKAGES := $(ALL_PACKAGES)
PACKAGE ?=
PACKAGE_MAKE_DIR ?= $(ROOT_PACKAGE_PROFILE_DIR)
PACKAGE_ALIASES := \
	agentic-flows=bijux-canon-runtime \
	bijux-agent=bijux-canon-agent \
	bijux-rag=bijux-canon-ingest \
	bijux-rar=bijux-canon-reason \
	bijux-vex=bijux-canon-index
VALID_PACKAGE_VALUES := $(ALL_PACKAGES) $(foreach mapping,$(PACKAGE_ALIASES),$(word 1,$(subst =, ,$(mapping))))

ROOT_MISSING_PACKAGE_FILES := $(filter-out $(ROOT_PACKAGE_PROFILE_FILES),$(ROOT_DECLARED_PACKAGE_FILES))
ROOT_UNDECLARED_PRIMARY_PACKAGES := $(filter-out $(PRIMARY_PACKAGES),$(ROOT_DISCOVERED_PRIMARY_PACKAGES))
ROOT_UNDECLARED_COMPAT_PACKAGES := $(filter-out $(COMPAT_PACKAGES),$(ROOT_DISCOVERED_COMPAT_PACKAGES))

ifneq ($(strip $(ROOT_MISSING_PACKAGE_FILES)),)
$(error Package manifest references missing profiles: $(ROOT_MISSING_PACKAGE_FILES))
endif

ifneq ($(strip $(ROOT_UNDECLARED_PRIMARY_PACKAGES)),)
$(error Undeclared primary package profiles found: $(ROOT_UNDECLARED_PRIMARY_PACKAGES))
endif

ifneq ($(strip $(ROOT_UNDECLARED_COMPAT_PACKAGES)),)
$(error Undeclared compatibility package profiles found: $(ROOT_UNDECLARED_COMPAT_PACKAGES))
endif

define resolve_package
$(strip \
$(if $(filter $(1),$(ALL_PACKAGES)),$(1), \
$(foreach mapping,$(PACKAGE_ALIASES), \
$(if $(filter $(1),$(word 1,$(subst =, ,$(mapping)))),$(word 2,$(subst =, ,$(mapping)))))))
endef

define assert_package
	@if [ -n "$(PACKAGE)" ] && [ -z "$(call resolve_package,$(PACKAGE))" ]; then \
	  echo "Unknown package '$(PACKAGE)'."; \
	  echo "Valid package values:"; \
	  printf "  %s\n" $(VALID_PACKAGE_VALUES); \
	  exit 2; \
	fi
endef
