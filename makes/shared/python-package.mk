# Resolve from this shared make fragment so package depth can change without
# forcing every consumer to recalculate the repository root.
MONOREPO_ROOT ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
PROJECT_DIR ?= $(CURDIR)
PROJECT_SLUG ?= $(notdir $(PROJECT_DIR))
CONFIG_DIR ?= $(MONOREPO_ROOT)/configs/$(PROJECT_SLUG)
MAKE_DIR ?= $(MONOREPO_ROOT)/makes/$(PROJECT_SLUG)
MKDOCS_CFG ?= $(CONFIG_DIR)/mkdocs.yml
ARTIFACTS_ROOT ?= $(MONOREPO_ROOT)/artifacts
PROJECT_ARTIFACTS_DIR ?= $(ARTIFACTS_ROOT)/$(PROJECT_SLUG)

.DELETE_ON_ERROR:
.DEFAULT_GOAL ?= all
.SHELLFLAGS ?= -eu -o pipefail -c
SHELL ?= bash
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(if $(shell test -x "$(VENV)/bin/python" && echo yes),$(VENV)/bin/python,python3)
ACT ?= $(VENV)/bin
RM ?= rm -rf

export MONOREPO_ROOT PROJECT_DIR PROJECT_SLUG CONFIG_DIR MAKE_DIR MKDOCS_CFG ARTIFACTS_ROOT PROJECT_ARTIFACTS_DIR
