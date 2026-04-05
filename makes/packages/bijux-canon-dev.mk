# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk

LINT_DIRS         := src/bijux_canon_dev tests
INTERROGATE_PATHS := src/bijux_canon_dev
QUALITY_PATHS     := src/bijux_canon_dev
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_canon_dev
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SKIP_MYPY         := 1
ENABLE_CODESPELL  := 1
ENABLE_MYPY       := 0
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
PUBLISH_UPLOAD_ENABLED := 0
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := $(COMMON_BUILD_CLEAN_PATHS)
PACKAGE_CLEAN_PATHS := \
  $(COMMON_PYTHON_CLEAN_PATHS) \
  $(COMMON_ARTIFACT_CLEAN_PATHS)
PACKAGE_ALL_TARGETS := clean install test lint quality security build sbom

include $(ROOT_MAKE_DIR)/package/primary.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

include $(ROOT_MAKE_DIR)/package/core-help.mk
