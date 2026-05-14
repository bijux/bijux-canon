PACKAGE_KIND := python
PACKAGE_IMPORT_NAME := bijux_canon_dev
SECURITY_IGNORE_IDS := PYSEC-2022-42969
ENABLE_CODESPELL  := 1
ENABLE_MYPY       := 1
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
BUILD_CHECK_DISTS := 1
PACKAGE_ALL_TARGETS := clean install test lint quality security build sbom
QUALITY_MYPY_CONFIG = $(MONOREPO_ROOT)/configs/mypy.ini
TEST_MAIN_ARGS := -m "not slow"

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
