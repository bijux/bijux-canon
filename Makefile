PRIMARY_PACKAGES := \
	bijux-llm-flows \
	bijux-llm-agent \
	bijux-llm-rag \
	bijux-llm-rar \
	bijux-llm-vex

COMPAT_PACKAGES := \
	compat-agentic-flows \
	compat-bijux-agent \
	compat-bijux-rag \
	compat-bijux-rar \
	compat-bijux-vex

ALL_PACKAGES := $(PRIMARY_PACKAGES) $(COMPAT_PACKAGES)
CHECK_PACKAGES := $(ALL_PACKAGES)
PACKAGE ?=

ARTIFACTS_ROOT := $(CURDIR)/artifacts
ROOT_ARTIFACTS_DIR := $(ARTIFACTS_ROOT)/root

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX := $(ROOT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME := $(ROOT_ARTIFACTS_DIR)/xdg_cache
export HYPOTHESIS_STORAGE_DIRECTORY := $(ROOT_ARTIFACTS_DIR)/hypothesis

DEFAULT_GOAL := help
.PHONY: \
	help list list-all lint quality security test docs api build sbom clean all \
	clean-root-artifacts

define resolve_package
$(strip \
$(if $(filter $(1),$(ALL_PACKAGES)),$(1), \
$(if $(filter $(1),agentic-flows),bijux-llm-flows, \
$(if $(filter $(1),bijux-agent),bijux-llm-agent, \
$(if $(filter $(1),bijux-rag),bijux-llm-rag, \
$(if $(filter $(1),bijux-rar),bijux-llm-rar, \
$(if $(filter $(1),bijux-vex),bijux-llm-vex)))))))
endef

define assert_package
	@if [ -n "$(PACKAGE)" ] && [ -z "$(call resolve_package,$(PACKAGE))" ]; then \
	  echo "Unknown package '$(PACKAGE)'."; \
	  echo "Valid package values:"; \
	  printf "  %s\n" $(ALL_PACKAGES) agentic-flows bijux-agent bijux-rag bijux-rar bijux-vex; \
	  exit 2; \
	fi
endef

define run_target
	@set -e; \
	resolved_package="$(call resolve_package,$(PACKAGE))"; \
	if [ -n "$$resolved_package" ]; then \
	  package_list="$$resolved_package"; \
	else \
	  package_list="$(2)"; \
	fi; \
	mkdir -p "$(ROOT_ARTIFACTS_DIR)"; \
	for package in $$package_list; do \
	  echo "==> $$package: $(1)"; \
	  $(MAKE) -C "packages/$$package" $(1); \
	done; \
	$(MAKE) clean-root-artifacts >/dev/null
endef

help:
	@printf "%s\n" \
	  "Targets:" \
	  "  list                List primary package slugs" \
	  "  list-all            List every package slug" \
	  "  test                Run tests package by package" \
	  "  lint                Run lint package by package" \
	  "  quality             Run quality package by package" \
	  "  security            Run security package by package" \
	  "  docs                Build docs package by package" \
	  "  api                 Run API checks package by package" \
	  "  build               Build package artifacts package by package" \
	  "  sbom                Generate package SBOMs package by package" \
	  "  clean               Clean package artifacts package by package" \
	  "  clean-root-artifacts Remove stray root-level caches outside artifacts/" \
	  "  all                 Run test, lint, quality, security, docs, api, build, sbom" \
	  "" \
	  "Use PACKAGE=<slug> to scope a target to one package." \
	  "Legacy PACKAGE aliases still resolve to the canonical bijux-llm-* package names."

list:
	@printf "%s\n" $(PRIMARY_PACKAGES)

list-all:
	@printf "%s\n" $(ALL_PACKAGES)

clean-root-artifacts:
	@rm -rf \
	  "$(CURDIR)/.hypothesis" \
	  "$(CURDIR)/.pytest_cache" \
	  "$(CURDIR)/.ruff_cache" \
	  "$(CURDIR)/.mypy_cache" \
	  "$(CURDIR)/.coverage" \
	  "$(CURDIR)/.coverage."* \
	  "$(CURDIR)/htmlcov" \
	  "$(CURDIR)/configs/.pytest_cache" \
	  "$(CURDIR)/configs/.ruff_cache" \
	  "$(CURDIR)/configs/.mypy_cache" \
	  "$(CURDIR)/configs/.hypothesis" || true

test:
	$(call assert_package)
	$(call run_target,test,$(PRIMARY_PACKAGES))

lint:
	$(call assert_package)
	$(call run_target,lint,$(CHECK_PACKAGES))

quality:
	$(call assert_package)
	$(call run_target,quality,$(CHECK_PACKAGES))

security:
	$(call assert_package)
	$(call run_target,security,$(CHECK_PACKAGES))

docs:
	$(call assert_package)
	$(call run_target,docs,$(PRIMARY_PACKAGES))

api:
	$(call assert_package)
	$(call run_target,api,$(PRIMARY_PACKAGES))

build:
	$(call assert_package)
	$(call run_target,build,$(PRIMARY_PACKAGES))

sbom:
	$(call assert_package)
	$(call run_target,sbom,$(PRIMARY_PACKAGES))

clean:
	$(call assert_package)
	$(call run_target,clean,$(ALL_PACKAGES))
	@$(MAKE) clean-root-artifacts

all: test lint quality security docs api build sbom
