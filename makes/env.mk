# Resolve from this shared make fragment so package depth can change without
# forcing every consumer to recalculate the repository root.
MONOREPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
PROJECT_DIR ?= $(CURDIR)
PROJECT_SLUG ?= $(notdir $(PROJECT_DIR))
ROOT_MAKE_DIR := $(MONOREPO_ROOT)/makes
CONFIG_DIR := $(MONOREPO_ROOT)/configs/$(PROJECT_SLUG)
API_DIR := $(MONOREPO_ROOT)/apis/$(PROJECT_SLUG)
MKDOCS_CFG := $(PROJECT_DIR)/mkdocs.yml
ARTIFACTS_ROOT := $(MONOREPO_ROOT)/artifacts
PROJECT_ARTIFACTS_DIR := $(ARTIFACTS_ROOT)/$(PROJECT_SLUG)

.DELETE_ON_ERROR:
.DEFAULT_GOAL ?= all
.SHELLFLAGS ?= -eu -o pipefail -c
SHELL ?= bash
PYTHON ?= $(shell command -v python3.11 || command -v python3)
UV ?= uv
VENV ?= $(PROJECT_ARTIFACTS_DIR)/venv
VENV_PYTHON ?= $(VENV)/bin/python
ACT ?= $(VENV)/bin
SELF_MAKE ?= $(if $(PACKAGE_PROFILE_MAKEFILE),$(MAKE) -f "$(PACKAGE_PROFILE_MAKEFILE)",$(MAKE))
override RM := rm -rf
DOCS_CONFIG_CLI ?= -m bijux_canon_dev.docs.mkdocs_config
DEPTRY_SCAN_SCRIPT ?= $(VENV_PYTHON) -m bijux_canon_dev.quality.deptry_scan
DEPTRY_CONFIG ?= $(MONOREPO_ROOT)/configs/deptry.toml
QUALITY_DEPTRY_COMMAND ?= $(DEPTRY_SCAN_SCRIPT) --deptry-bin "$(DEPTRY)" --config "$(DEPTRY_CONFIG)" --project-dir . $(QUALITY_PATHS)
SECURITY_PIP_AUDIT_TEXT_COMMAND ?= "$(VENV_PYTHON)" -m bijux_canon_dev.security.pip_audit_gate
SBOM_VERSION_RESOLVER ?= -m bijux_canon_dev.release.version_resolver
SBOM_REQUIREMENTS_WRITER ?= -m bijux_canon_dev.sbom.requirements_writer
COMMON_BUILD_CLEAN_PATHS := build dist *.egg-info
COMMON_PYTHON_CLEAN_PATHS := \
	.pytest_cache htmlcov coverage.xml \
	$(COMMON_BUILD_CLEAN_PATHS) \
	.tox .nox .ruff_cache .mypy_cache .hypothesis \
	.coverage.* .coverage .benchmarks .cache
COMMON_API_TEMP_CLEAN_PATHS := spec.json openapitools.json node_modules site
COMMON_ARTIFACT_CLEAN_PATHS := artifacts "$(PROJECT_ARTIFACTS_DIR)"
COMMON_CONFIG_CACHE_CLEAN_PATHS := "$(CONFIG_DIR)/.ruff_cache"

ifneq ($(strip $(PACKAGE_PROFILE_MAKEFILE)),)
MAKEFLAGS += -f $(PACKAGE_PROFILE_MAKEFILE)
endif

export PYTHONDONTWRITEBYTECODE ?= 1
export PYTHONPYCACHEPREFIX ?= $(PROJECT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME ?= $(PROJECT_ARTIFACTS_DIR)/xdg_cache
export HYPOTHESIS_STORAGE_DIRECTORY ?= $(PROJECT_ARTIFACTS_DIR)/hypothesis
export COVERAGE_FILE ?= $(PROJECT_ARTIFACTS_DIR)/test/.coverage
export UV_CACHE_DIR ?= $(PROJECT_ARTIFACTS_DIR)/uv_cache
export NPM_CONFIG_CACHE ?= $(PROJECT_ARTIFACTS_DIR)/npm_cache
export PYTHONPATH ?=
export PYTHONPATH := $(MONOREPO_ROOT)/packages/bijux-canon-dev/src$(if $(PYTHONPATH),:$(PYTHONPATH))

export MONOREPO_ROOT PROJECT_DIR PROJECT_SLUG ROOT_MAKE_DIR CONFIG_DIR API_DIR MKDOCS_CFG ARTIFACTS_ROOT PROJECT_ARTIFACTS_DIR
