include $(CURDIR)/makes/root/packages.mk

ARTIFACTS_ROOT := $(CURDIR)/artifacts
ROOT_ARTIFACTS_DIR := $(ARTIFACTS_ROOT)/root
ROOT_CHECK_VENV := $(ROOT_ARTIFACTS_DIR)/check-venv
ROOT_CHECK_PYTHON := $(ROOT_CHECK_VENV)/bin/python
ROOT_CHECK_STAMP := $(ROOT_ARTIFACTS_DIR)/.check-tools.stamp
ROOT_DOCS_ARTIFACTS_DIR := $(ROOT_ARTIFACTS_DIR)/docs
ROOT_DOCS_BUILD_SITE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/build-site
ROOT_DOCS_CHECK_SITE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/check-site
ROOT_DOCS_SERVE_SITE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/serve-site
ROOT_DOCS_CACHE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/cache
ROOT_DOCS_SERVE_CFG := $(ROOT_DOCS_ARTIFACTS_DIR)/mkdocs.serve.yml
ROOT_DOCS_DEV_ADDR ?= 127.0.0.1:8001
ROOT_DOCS_ENV := NO_MKDOCS_2_WARNING=true

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX := $(ROOT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME := $(ROOT_ARTIFACTS_DIR)/xdg_cache
export HYPOTHESIS_STORAGE_DIRECTORY := $(ROOT_ARTIFACTS_DIR)/hypothesis
export PYTHONPATH := $(CURDIR)/packages/bijux-canon-dev/src$(if $(PYTHONPATH),:$(PYTHONPATH))

include $(CURDIR)/makes/root/dispatch.mk
include $(CURDIR)/makes/root/toolchain.mk
include $(CURDIR)/makes/root/cleanup.mk
include $(CURDIR)/makes/root/docs.mk

DEFAULT_GOAL := help
.PHONY: \
	help list list-all lint quality security test docs docs-check docs-serve api build sbom clean all \
	clean-root-artifacts root-check-env

help:
	@printf "%s\n" \
	  "Targets:" \
	  "  list                List primary package slugs" \
	  "  list-all            List every package slug" \
	  "  test                Run tests package by package" \
	  "  lint                Run lint package by package" \
	  "  quality             Run quality package by package" \
	  "  security            Run security package by package" \
	  "  docs                Build the monorepo docs site from root/docs" \
	  "  api                 Run API checks package by package" \
	  "  build               Build package artifacts package by package" \
	  "  sbom                Generate package SBOMs package by package" \
	  "  clean               Clean package artifacts package by package" \
	  "  clean-root-artifacts Remove stray root-level caches outside artifacts/" \
	  "  all                 Run test, lint, quality, security, docs, api, build, sbom" \
	  "" \
	  "Use PACKAGE=<slug> to scope a target to one package." \
	  "Legacy PACKAGE aliases still resolve to the canonical bijux-canon-* package names."

list:
	@printf "%s\n" $(PRIMARY_PACKAGES)

list-all:
	@printf "%s\n" $(ALL_PACKAGES)

all: test lint quality security docs api build sbom
