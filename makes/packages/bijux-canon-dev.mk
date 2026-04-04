# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package-profile.mk

LINT_DIRS         := src/bijux_canon_dev tests
INTERROGATE_PATHS := src/bijux_canon_dev
QUALITY_PATHS     := src/bijux_canon_dev
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_canon_dev
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SKIP_MYPY         := 1
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
PUBLISH_UPLOAD_ENABLED := 0
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := $(COMMON_BUILD_CLEAN_PATHS)
PACKAGE_CLEAN_PATHS := \
  $(COMMON_PYTHON_CLEAN_PATHS) \
  $(COMMON_ARTIFACT_CLEAN_PATHS)
PACKAGE_ALL_TARGETS := clean install test lint quality security build sbom

include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/test.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/sbom.mk
include $(ROOT_MAKE_DIR)/publish.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

##@ Core
clean: ## Remove virtualenv plus caches and artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install project in editable mode into .venv
bootstrap: ## Setup environment
all: ## Run clean → install → test → lint
help: ## Show this help
