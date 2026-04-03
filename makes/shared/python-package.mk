MONOREPO_ROOT ?= $(abspath $(CURDIR)/..)
PROJECT_DIR ?= $(CURDIR)
PROJECT_SLUG ?= $(notdir $(PROJECT_DIR))
CONFIG_DIR ?= $(MONOREPO_ROOT)/configs/$(PROJECT_SLUG)
MAKE_DIR ?= $(MONOREPO_ROOT)/makes/$(PROJECT_SLUG)

.DELETE_ON_ERROR:
.DEFAULT_GOAL ?= all
.SHELLFLAGS ?= -eu -o pipefail -c
SHELL ?= bash
PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON ?= $(if $(shell test -x "$(VENV)/bin/python" && echo yes),$(VENV)/bin/python,python3)
ACT ?= $(VENV)/bin
RM ?= rm -rf

export MONOREPO_ROOT PROJECT_DIR PROJECT_SLUG CONFIG_DIR MAKE_DIR
