include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk
include $(ROOT_MAKE_DIR)/package/api-python-package.mk

PACKAGE_IMPORT_NAME := bijux_canon_agent
MYPY_CONFIG          := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_FLAGS           := --follow-imports silent --ignore-missing-imports --strict-optional --disallow-untyped-defs --warn-return-any --check-untyped-defs
MYPY_TARGETS         := src/bijux_canon_agent/contracts src/bijux_canon_agent/pipeline src/bijux_canon_agent/traces src/bijux_canon_agent/llm src/bijux_canon_agent/agents/base.py
MYPY_CORE_CONFIG     := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_CORE_FLAGS      := $(MYPY_FLAGS)
MYPY_CORE_TARGETS    := $(MYPY_TARGETS)
MYPY_EXTENDED_CONFIG := $(MONOREPO_ROOT)/configs/mypy.ini
MYPY_EXTENDED_FLAGS  := --follow-imports silent --ignore-missing-imports --strict-optional --no-warn-unused-ignores --no-warn-return-any --no-check-untyped-defs
MYPY_EXTENDED_TARGETS := src/bijux_canon_agent/agents src/bijux_canon_agent/application src/bijux_canon_agent/config src/bijux_canon_agent/interfaces src/bijux_canon_agent/observability src/bijux_canon_agent/pipeline src/bijux_canon_agent/tooling/example_pipelines src/bijux_canon_agent/core tests
ENABLE_PYTYPE        := 1
QUALITY_MYPY_CONFIG  := $(MONOREPO_ROOT)/configs/mypy.ini
QUALITY_MYPY_FLAGS   := $(MYPY_FLAGS)
QUALITY_MYPY_TARGETS := $(MYPY_TARGETS)
SKIP_MYPY            := 0
QUALITY_VULTURE_MIN_CONFIDENCE := 90
SECURITY_IGNORE_IDS  := PYSEC-2022-42969 CVE-2026-21860
API_MODULE           := bijux_canon_agent.api.v1.app
API_FACTORY          := create_app
API_SKIP_IF_NO_SCHEMAS := 1
API_LINT_MISSING_MESSAGE := → No API schemas found under $(API_DIR); skipping API lint
API_TEST_MISSING_MESSAGE := → No API schemas found under $(API_DIR); skipping API tests
API_NODE_BOOTSTRAP_MODE := npm-install-pinned
OPENAPI_GENERATOR_NPM_PACKAGE := @openapitools/openapi-generator-cli@2.27.0
OPENAPI_GENERATOR_JAR_VERSION := 7.18.0
API_VALIDATE_IN_NODE_DIR := 1
SCHEMATHESIS_OPTS    = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --suppress-health-check=filter_too_much
BUILD_CLEAN_PYCACHE  := 1
PUBLISH_VERIFY_INSTALL_CMD := python -m bijux_canon_agent --help >/dev/null 2>&1
TEST_MAIN_ARGS       := -m "not integration and not e2e"
TEST_UNIT_DIR_ARGS   := -m "not integration and not e2e and not slow" --maxfail=1 -q
TEST_UNIT_FALLBACK_ARGS := -k "not e2e and not integration and not functional" -m "not integration and not e2e and not slow" --maxfail=1 -q
TEST_SYNTAX_PATHS    := src tests
TEST_PYCACHE_PREFIX  = $(TEST_ARTIFACTS_DIR)/pycache
TEST_RESET_PYCACHE   := 1
TEST_PRE_TARGETS     := bootstrap

include $(ROOT_MAKE_DIR)/package/gates.mk

ci-fast: lint test mypy-core
.PHONY: ci-fast
