# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../bijux-py/root-env.mk

ARTIFACTS_ROOT := $(CURDIR)/artifacts
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
UV_SYNC := UV_PROJECT_ENVIRONMENT="$(ROOT_CHECK_VENV)" $(UV) sync --frozen --group dev --python "$(PYTHON)"

export PYTHONPATH := $(CURDIR)/packages/bijux-canon-dev/src$(if $(PYTHONPATH),:$(PYTHONPATH))
