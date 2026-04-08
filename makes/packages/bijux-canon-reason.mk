# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk
include $(ROOT_MAKE_DIR)/package/canon-contract-service.mk

PACKAGE_IMPORT_NAME := bijux_canon_reason
ENABLE_MYPY := 0
API_MODULE := bijux_canon_reason.api.v1.app
API_INSTALL_EDITABLE := 1
API_NODE_BOOTSTRAP_MODE := npm-ci-sandbox
API_SCHEMATHESIS_FILTER_MODE := warnings
API_ENABLE_REPRO := 1
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance --suppress-health-check=filter_too_much
BUILD_CLEAN_PYCACHE := 1
PUBLISH_VERIFY_INSTALL_CMD := bijux --version
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_reason/core) $(abspath src/bijux_canon_reason/interfaces)
TEST_MAIN_ARGS := --maxfail=1
ENABLE_BENCH := 0

include $(ROOT_MAKE_DIR)/package/gates.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk
