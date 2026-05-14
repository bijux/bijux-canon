PACKAGE_KIND := api-python
PACKAGE_IMPORT_NAME := bijux_canon_reason
ENABLE_MYPY := 1
API_MODULE := bijux_canon_reason.api.v1.app
API_INSTALL_EDITABLE := 1
API_NODE_BOOTSTRAP_MODE := npm-ci-sandbox
API_SCHEMATHESIS_FILTER_MODE := warnings
API_ENABLE_REPRO := 1
SCHEMATHESIS = $(PROJECT_DIR)/tooling/schemathesis_exit_guard.py
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance --suppress-health-check=filter_too_much --warnings off
BUILD_CLEAN_PYCACHE := 1
PUBLISH_VERIFY_INSTALL_CMD := bijux --version
TEST_COVERAGE_TARGETS := $(abspath src/bijux_canon_reason/core) $(abspath src/bijux_canon_reason/interfaces)
TEST_MAIN_ARGS := -m "not slow" --maxfail=1

test-all: TEST_MAIN_ARGS =
test-all: PYTEST_ADDOPTS_EXTRA = -o timeout=0
test-all: test
.PHONY: test-all

test-all-plus-run-time: TEST_MAIN_ARGS =
test-all-plus-run-time: PYTEST_ADDOPTS_EXTRA = -o timeout=0 --durations=0 --durations-min=0
test-all-plus-run-time: test
.PHONY: test-all-plus-run-time

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

PACKAGE_INSTALL_PYTHON_PACKAGES := uv==0.11.7
