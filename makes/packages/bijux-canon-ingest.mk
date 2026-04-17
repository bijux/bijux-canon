PACKAGE_KIND := api-python
PACKAGE_IMPORT_NAME            := bijux_canon_ingest
PACKAGE_LINT_EXTRA_DIRS        := stubs
PACKAGE_CLEAN_EXTRA_PATHS      := site
RUFF_CONFIG                    := pyproject.toml
MYPY_TARGETS                   = $(if $(LINT_SCOPE),$(LINT_SCOPE),src/bijux_canon_ingest)
MYPY_CONFIG                    := pyproject.toml
MYPY_FLAGS                     :=
ENABLE_CODESPELL               := 0
ENABLE_RADON                   := 0
ENABLE_PYDOCSTYLE              := 0
FMT_RUN_RUFF_CHECK_FIX         := 1
SECURITY_IGNORE_IDS            := PYSEC-2022-42969
SECURITY_BANDIT_SKIP_IDS       := B101,B311
BANDIT_FLAGS                   := --severity-level high --confidence-level high
BANDIT_EXCLUDES                := artifacts,build,dist,.tox,.mypy_cache,.pytest_cache,tests
PIP_AUDIT_CONSOLE_FLAGS        := --progress-spinner off
API_MODE                       := live-contract
API_SCHEMA                     = $(API_DIR)/v1/schema.yaml
API_SERVER_IMPORT              := bijux_canon_ingest.interfaces.http.app:create_app
API_DRIFT_OUT                  = $(API_ARTIFACTS_DIR)/openapi.generated.json
API_OPENAPI_DRIFT_COMMAND      = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_ingest.interfaces.http.app:create_app --schema "$(API_SCHEMA)" --out "$(API_DRIFT_OUT)"
API_SCHEMATHESIS_ARGS          := --workers=1 --max-failures=1 --checks=not_a_server_error,response_schema_conformance,content_type_conformance,response_headers_conformance --max-examples=5 --request-timeout=30000 --max-response-time=500 --suppress-health-check=filter_too_much
BUILD_CHECK_DISTS              := 1
PACKAGE_INSTALL_TARGETS := \
  test lint fmt quality security api build sbom \
  fmt-artifacts lint-artifacts interrogate-report
PACKAGE_ALL_TARGETS := clean install test lint quality security api build sbom

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

PACKAGE_INSTALL_PYTHON_PACKAGES := uv==0.11.7
