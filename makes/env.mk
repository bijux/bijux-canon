# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

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
