# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk

LINT_DIRS         := src/bijux_canon_reason
ENABLE_MYPY       := 0
ENABLE_CODESPELL  := 1
ENABLE_RADON      := 1
ENABLE_PYDOCSTYLE := 0
ENABLE_PYTYPE     := 0
RUFF_CHECK_FIX    := 1
INTERROGATE_PATHS := src/bijux_canon_reason
QUALITY_PATHS     := src/bijux_canon_reason
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS    := src/bijux_canon_reason
SECURITY_IGNORE_IDS := PYSEC-2022-42969
API_MODE := contract
API_MODULE := bijux_canon_reason.api.v1.app
API_INSTALL_EDITABLE := 1
API_NODE_BOOTSTRAP_MODE := npm-ci-sandbox
API_SCHEMATHESIS_FILTER_MODE := warnings
API_ENABLE_REPRO := 1
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS := 1
BUILD_CLEAN_PATHS := $(COMMON_BUILD_CLEAN_PATHS)
BUILD_CLEAN_PYCACHE := 1
PUBLISH_VERIFY_INSTALL_CMD := bijux --version
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_reason/core) $(abspath src/bijux_canon_reason/interfaces)
TEST_MAIN_ARGS := --maxfail=1
ENABLE_BENCH := 0
PACKAGE_BOOTSTRAP_TARGETS := lint quality security api
PACKAGE_CLEAN_PATHS := \
  $(COMMON_PYTHON_CLEAN_PATHS) demo .tmp_home \
  $(COMMON_API_TEMP_CLEAN_PATHS) \
  docs/reference $(COMMON_ARTIFACT_CLEAN_PATHS) usage_test usage_test_artifacts \
  $(COMMON_CONFIG_CACHE_CLEAN_PATHS)
PACKAGE_ALL_TARGETS := clean install test lint quality security api build sbom
PACKAGE_DEFINE_ALL_PARALLEL := 1

include $(ROOT_MAKE_DIR)/package/primary.mk
include $(ROOT_MAKE_DIR)/package/parallel.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

include $(ROOT_MAKE_DIR)/package/core-help.mk
