include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../bijux-py/package-profile.mk
PACKAGE_IMPORT_NAME := bijux_canon_runtime

include $(ROOT_MAKE_DIR)/bijux-py/package-workspace-python.mk

SECURITY_EXTRA_CHECKS := $(MONOREPO_ROOT)/packages/bijux-canon-dev/src/bijux_canon_dev/packages/runtime/check_dependency_allowlist.py
# The checked-in schema already includes the /api/v1 prefix in each path.
# Leave the schemathesis base URL at the API root to avoid duplicating it.
API_BASE_PATH :=
API_MODULE := bijux_canon_runtime.api.v1.app
API_OPENAPI_DRIFT_COMMAND = $(VENV_PYTHON) -m bijux_canon_dev.api.openapi_drift --app-import bijux_canon_runtime.api.v1.app:app --schema "$(API_DIR)/v1/schema.yaml" --out "$(API_ARTIFACTS_DIR)/openapi.generated.json"
SCHEMATHESIS_OPTS = --checks=all --max-failures=1 --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) --request-timeout=5 --max-response-time=3 --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,not_a_server_error --suppress-health-check=filter_too_much
BUILD_RELEASE_DRY_RUN_CMD := $(VENV_PYTHON) -c 'from packaging.version import Version; import importlib.metadata as m; from pathlib import Path; import sys; version=m.version("bijux-canon-runtime"); base=Version(version).base_version; print(f"version={version} base={base}"); changelog=Path("CHANGELOG.md").read_text().splitlines(); header=f"## {base}"; sys.exit(f"Missing changelog header for {base}") if header not in changelog else None; idx=changelog.index(header); section_lines=changelog[idx + 1:]; end_idx=next((i for i, line in enumerate(section_lines) if line.startswith("## ")), None); section="\n".join(section_lines[:end_idx] if end_idx is not None else section_lines); required=["### Added","### Changed","### Fixed"]; missing=[h for h in required if h not in section]; sys.exit(f"Changelog {base} missing sections: {missing}") if missing else None; print("✔ Changelog sections present")'

include $(ROOT_MAKE_DIR)/bijux-py/package-gates.mk

-include .env
export
