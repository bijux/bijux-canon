PACKAGE_KIND := python
PACKAGE_IMPORT_NAME := bijux_canon_dev
SECURITY_IGNORE_IDS :=
ENABLE_CODESPELL  := 1
CODESPELL         = $(VENV_PYTHON) -m codespell_lib --ignore-words-list=ND,nd,intoto
ENABLE_MYPY       := 1
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
BUILD_CHECK_DISTS := 1
PACKAGE_ALL_TARGETS := clean install test lint quality security build sbom
QUALITY_MYPY_CONFIG = $(MONOREPO_ROOT)/configs/mypy.ini
TEST_MAIN_ARGS := -m "not slow"
TEST_COVERAGE_TARGETS := $(abspath tests)
TEST_COVERAGE_FAIL_UNDER := 40
SEMVER_BASELINE_REF := v0.3.9
TEST_PRE_TARGETS := bootstrap semver-baseline

.PHONY: semver-baseline
semver-baseline:
	@if ! git -C "$(MONOREPO_ROOT)" rev-parse --verify "$(SEMVER_BASELINE_REF)^{commit}" >/dev/null 2>&1; then \
	  echo "→ Fetching semver baseline $(SEMVER_BASELINE_REF)"; \
	  git -C "$(MONOREPO_ROOT)" fetch --no-tags --depth=1 origin \
	    "refs/tags/$(SEMVER_BASELINE_REF):refs/tags/$(SEMVER_BASELINE_REF)"; \
	fi

test-all: TEST_MAIN_ARGS =
test-all: PYTEST_ADDOPTS_EXTRA = -o timeout=0
test-all: test
.PHONY: test-all

test-all-plus-run-time: TEST_MAIN_ARGS =
test-all-plus-run-time: PYTEST_ADDOPTS_EXTRA = -o timeout=0 --durations=0 --durations-min=0
test-all-plus-run-time: test
.PHONY: test-all-plus-run-time

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

PACKAGE_INSTALL_PYTHON_PACKAGES := uv==0.11.24
