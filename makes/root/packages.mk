# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

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
PACKAGE_MAKE_DIR ?= $(CURDIR)/makes/packages
PACKAGE_ALIASES := \
	agentic-flows=bijux-canon-runtime \
	bijux-agent=bijux-canon-agent \
	bijux-rag=bijux-canon-ingest \
	bijux-rar=bijux-canon-reason \
	bijux-vex=bijux-canon-index
VALID_PACKAGE_VALUES := $(ALL_PACKAGES) $(foreach mapping,$(PACKAGE_ALIASES),$(word 1,$(subst =, ,$(mapping))))

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
