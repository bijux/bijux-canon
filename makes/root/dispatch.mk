# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

ROOT_PACKAGE_TARGETS := test lint quality security api build sbom clean

ROOT_TARGET_PACKAGES_test := $(PRIMARY_PACKAGES)
ROOT_TARGET_PACKAGES_lint := $(CHECK_PACKAGES)
ROOT_TARGET_PACKAGES_quality := $(CHECK_PACKAGES)
ROOT_TARGET_PACKAGES_security := $(CHECK_PACKAGES)
ROOT_TARGET_PACKAGES_api := $(PRIMARY_PACKAGES)
ROOT_TARGET_PACKAGES_build := $(PRIMARY_PACKAGES)
ROOT_TARGET_PACKAGES_sbom := $(PRIMARY_PACKAGES)
ROOT_TARGET_PACKAGES_clean := $(ALL_PACKAGES)

ROOT_TARGET_SHARED_ENV_test := 0
ROOT_TARGET_SHARED_ENV_lint := 1
ROOT_TARGET_SHARED_ENV_quality := 1
ROOT_TARGET_SHARED_ENV_security := 1
ROOT_TARGET_SHARED_ENV_api := 0
ROOT_TARGET_SHARED_ENV_build := 0
ROOT_TARGET_SHARED_ENV_sbom := 0
ROOT_TARGET_SHARED_ENV_clean := 0

ROOT_TARGET_POST_clean = @$(MAKE) clean-root-artifacts

define run_root_package_target
	@set -eu; \
	resolved_package="$(call resolve_package,$(PACKAGE))"; \
	if [ -n "$$resolved_package" ]; then \
	  package_list="$$resolved_package"; \
	else \
	  package_list="$(2)"; \
	fi; \
	mkdir -p "$(ROOT_ARTIFACTS_DIR)"; \
	cleanup() { $(MAKE) clean-root-artifacts >/dev/null; }; \
	trap cleanup EXIT; \
	if [ "$(3)" = "1" ]; then \
	  $(MAKE) root-check-env >/dev/null; \
	fi; \
	failures=""; \
	for package in $$package_list; do \
	  profile_path="$(PACKAGE_MAKE_DIR)/$$package.mk"; \
	  if [ ! -f "$$profile_path" ]; then \
	    echo "Missing package profile: $$profile_path"; \
	    failures="$$failures $$package"; \
	    continue; \
	  fi; \
	  echo "==> $$package: $(1)"; \
	  if [ "$(3)" = "1" ]; then \
	    if ! $(MAKE) -C "packages/$$package" -f "$$profile_path" \
	      VENV="$(ROOT_CHECK_VENV)" \
	      VENV_PYTHON="$(ROOT_CHECK_PYTHON)" \
	      PYTHON="$(ROOT_CHECK_PYTHON)" \
	      ACT="$(ROOT_CHECK_VENV)/bin" \
	      $(1); then \
	      failures="$$failures $$package"; \
	    fi; \
	  elif ! $(MAKE) -C "packages/$$package" -f "$$profile_path" $(1); then \
	    failures="$$failures $$package"; \
	  fi; \
	done; \
	if [ -n "$$failures" ]; then \
	  echo; \
	  echo "Packages with $(1) failures:$$failures"; \
	  exit 2; \
	fi
endef

define define_root_package_target
$(1):
	$$(call assert_package)
	$$(call run_root_package_target,$(1),$$(ROOT_TARGET_PACKAGES_$(1)),$$(ROOT_TARGET_SHARED_ENV_$(1)))
	$$(ROOT_TARGET_POST_$(1))
endef

$(foreach target,$(ROOT_PACKAGE_TARGETS),$(eval $(call define_root_package_target,$(target))))

##@ Orchestration
test: ## Run primary package tests package by package
lint: ## Run repository lint checks package by package with the shared check environment
quality: ## Run repository quality checks package by package with the shared check environment
security: ## Run repository security checks package by package with the shared check environment
api: ## Run primary package API checks package by package
build: ## Build primary package artifacts package by package
sbom: ## Generate primary package SBOMs package by package
clean: ## Clean package artifacts across the repository
