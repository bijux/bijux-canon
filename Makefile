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
ROOT_CHECK_VENV := $(ROOT_ARTIFACTS_DIR)/check-venv
ROOT_CHECK_PYTHON := $(ROOT_CHECK_VENV)/bin/python
ROOT_CHECK_STAMP := $(ROOT_ARTIFACTS_DIR)/.check-tools.stamp
ROOT_CHECK_BOOTSTRAP_PYTHON := $(shell command -v python3.11 || command -v python3)
ROOT_CHECK_PACKAGES := \
	bandit \
	codespell \
	deptry \
	interrogate \
	mkdocs \
	mkdocs-click \
	mkdocs-gen-files \
	mkdocs-git-revision-date-localized-plugin \
	mkdocs-glightbox \
	mkdocs-include-markdown-plugin \
	mkdocs-literate-nav \
	mkdocs-material \
	mkdocs-minify-plugin \
	mkdocs-redirects \
	mkdocs-section-index \
	mkdocstrings \
	mypy \
	pydantic \
	pip-audit \
	pydocstyle \
	pymdown-extensions \
	radon \
	ruff \
	vulture

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX := $(ROOT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME := $(ROOT_ARTIFACTS_DIR)/xdg_cache
export HYPOTHESIS_STORAGE_DIRECTORY := $(ROOT_ARTIFACTS_DIR)/hypothesis

DEFAULT_GOAL := help
.PHONY: \
	help list list-all lint quality security test docs api build sbom clean all \
	clean-root-artifacts root-check-env

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
	  echo "==> $$package: $(1)"; \
	  if [ "$(3)" = "1" ]; then \
	    if ! $(MAKE) -o install -o bootstrap -o ensure-venv -C "packages/$$package" \
	      VENV="$(ROOT_CHECK_VENV)" \
	      VENV_PYTHON="$(ROOT_CHECK_PYTHON)" \
	      PYTHON="$(ROOT_CHECK_PYTHON)" \
	      ACT="$(ROOT_CHECK_VENV)/bin" \
	      $(1); then \
	      failures="$$failures $$package"; \
	    fi; \
	  elif ! $(MAKE) -C "packages/$$package" $(1); then \
	    failures="$$failures $$package"; \
	  fi; \
	done; \
	if [ -n "$$failures" ]; then \
	  echo; \
	  echo "Packages with $(1) failures:$$failures"; \
	  exit 2; \
	fi
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
	  "$(CURDIR)/.benchmarks" \
	  "$(CURDIR)/htmlcov" \
	  "$(CURDIR)/configs/.pytest_cache" \
	  "$(CURDIR)/configs/.ruff_cache" \
	  "$(CURDIR)/configs/.mypy_cache" \
	  "$(CURDIR)/configs/.hypothesis" || true

root-check-env: $(ROOT_CHECK_STAMP)

$(ROOT_CHECK_STAMP):
	@mkdir -p "$(ROOT_ARTIFACTS_DIR)"
	@rm -rf "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_BOOTSTRAP_PYTHON)" -m venv "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade pip setuptools wheel >/dev/null
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade $(ROOT_CHECK_PACKAGES) >/dev/null
	@touch "$(ROOT_CHECK_STAMP)"

test:
	$(call assert_package)
	$(call run_target,test,$(PRIMARY_PACKAGES))

lint:
	$(call assert_package)
	$(call run_target,lint,$(CHECK_PACKAGES),1)

quality:
	$(call assert_package)
	$(call run_target,quality,$(CHECK_PACKAGES),1)

security:
	$(call assert_package)
	$(call run_target,security,$(CHECK_PACKAGES),1)

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
