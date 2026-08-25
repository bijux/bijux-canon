PACKAGE_KIND := workspace-python
PACKAGE_IMPORT_NAME := bijux_canon_runtime
MYPY_TARGETS := $(if $(LINT_SCOPE),$(LINT_SCOPE),src/bijux_canon_runtime)
TEST_CI_TARGETS := test-unit test-e2e test-regression
TEST_MAIN_ARGS := -m "not slow and not real_local and not api"
TEST_E2E_ARGS := -m "e2e and not slow" --maxfail=1 -q
TEST_REGRESSION_ARGS := -m "regression and not slow" --maxfail=1 -q
TEST_EVALUATION_ARGS := -m "evaluation and not slow" --maxfail=1 -q
TEST_REAL_LOCAL_ARGS := -m "real_local and not slow" -s -p no:cov
TEST_COVERAGE_TARGETS := $(abspath tests/unit)
TEST_COVERAGE_FAIL_UNDER := 70
test-e2e test-regression: PYTEST_ADDOPTS_EXTRA = --no-cov

SECURITY_EXTRA_CHECKS = $(MONOREPO_ROOT)/packages/bijux-canon-dev/src/bijux_canon_dev/packages/runtime/check_dependency_allowlist.py
# The checked-in schema includes the complete /api/v2 path for every operation.
# Leave the Schemathesis base URL at the API root and supply the required
# version-negotiation header to every generated request.
RUNTIME_API_ROOT := $(API_DIR)
override API_DIR := $(RUNTIME_API_ROOT)/v2
API_MODE := contract
API_BASE_PATH :=
API_MODULE := bijux_canon_runtime.api.v2.app
HEALTH_PATH := /openapi.json
API_INSTALL_PYTHON_PACKAGES := prance openapi-spec-validator uvicorn schemathesis fastapi starlette
API_OPENAPI_DRIFT_COMMAND = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_runtime.api.v2.app:app --schema "$(API_DIR)/schema.yaml" --out "$(API_ARTIFACTS_DIR)/openapi.generated.json"
SCHEMATHESIS_OPTS = --checks=response_schema_conformance,content_type_conformance,response_headers_conformance --max-failures=1 --request-timeout=30 --max-response-time=5 --max-examples=5 --generation-deterministic --suppress-health-check=filter_too_much --header 'Bijux-API-Version:v2'
API_TEST_WORKSPACE = $(API_ARTIFACTS_DIR)/workspace
export BIJUX_CANON_RUNTIME_WORKING_ROOT = $(API_TEST_WORKSPACE)

.PHONY: api-test-workspace
api-test-workspace:
	@mkdir -p "$(API_ARTIFACTS_DIR)"
	@PYTHONPATH="$(PROJECT_DIR)/src$${PYTHONPATH:+:$$PYTHONPATH}" \
	  "$(VENV_PYTHON)" -c 'from bijux_canon_runtime.interfaces.cli.entrypoint import main; raise SystemExit(main())' \
	  init --workspace "$(API_TEST_WORKSPACE)" --json \
	  >"$(API_ARTIFACTS_DIR)/workspace-initialization.json"

api-test: api-test-workspace
openapi-drift: api-test-workspace

.PHONY: api-versioned-freeze
api-versioned-freeze:
	@$(CANON_DEV_PYTHON_ENV) "$(VENV_PYTHON)" -m bijux_canon_dev.api.freeze_contracts --repo-root "$(MONOREPO_ROOT)"

api: openapi-drift api-versioned-freeze
BUILD_RELEASE_DRY_RUN_CMD = $(VENV_PYTHON) -c 'from packaging.version import Version; import importlib.metadata as m; from pathlib import Path; import sys; version=m.version("bijux-canon-runtime"); base=Version(version).base_version; print(f"version={version} base={base}"); changelog=Path("CHANGELOG.md").read_text().splitlines(); header=f"## {base}"; sys.exit(f"Missing changelog header for {base}") if header not in changelog else None; idx=changelog.index(header); section_lines=changelog[idx + 1:]; end_idx=next((i for i, line in enumerate(section_lines) if line.startswith("## ")), None); section="\n".join(section_lines[:end_idx] if end_idx is not None else section_lines); required=["### Added","### Changed","### Fixed"]; missing=[h for h in required if h not in section]; sys.exit(f"Changelog {base} missing sections: {missing}") if missing else None; print("✔ Changelog sections present")'
RUNTIME_WORKSPACE_INSTALL_COMMAND = $(CANON_DEV_PYTHON_ENV) "$(VENV_PYTHON)" -m bijux_canon_dev.release.workspace_install --repo "$(MONOREPO_ROOT)" --package-dir "$(PROJECT_DIR)" --extras "$$EXTRAS"
WORKSPACE_DEPENDENCY_PATHS = $(RUNTIME_WORKSPACE_INSTALL_COMMAND) --kind local
WORKSPACE_EXTERNAL_DEPENDENCIES = $(RUNTIME_WORKSPACE_INSTALL_COMMAND) --kind external

test-all: TEST_MAIN_ARGS =
test-all: PYTEST_ADDOPTS_EXTRA = -o timeout=0
test-all: test
.PHONY: test-all

test-all-plus-run-time: TEST_MAIN_ARGS =
test-all-plus-run-time: PYTEST_ADDOPTS_EXTRA = -o timeout=0 --durations=0 --durations-min=0
test-all-plus-run-time: test
.PHONY: test-all-plus-run-time

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

-include .env
export

PACKAGE_INSTALL_PYTHON_PACKAGES := uv==0.11.24
