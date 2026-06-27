BIJUX_REPOSITORY_ENV_OVERLAY_INCLUDED := 1

MONOREPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
ROOT_MAKE_DIR := $(MONOREPO_ROOT)/makes
CONFIG_DIR := $(MONOREPO_ROOT)/configs
CANON_DEV_SRC := $(MONOREPO_ROOT)/packages/bijux-canon-dev/src
CANON_DEV_PYTHON_ENV ?= PYTHONPATH="$(CANON_DEV_SRC)$${PYTHONPATH:+:$$PYTHONPATH}"
DOCS_CONFIG_CLI ?= -m bijux_canon_dev.docs.mkdocs_config
CODESPELL ?= $(VENV_PYTHON) -m codespell_lib
QUALITY_GATE_PYTHON ?= $(if $(wildcard $(VENV_PYTHON)),$(abspath $(VENV_PYTHON)),$(if $(wildcard $(VENV)/bin/python),$(abspath $(VENV)/bin/python),$(PYTHON)))
DEPTRY_SCAN_SCRIPT ?= $(CANON_DEV_PYTHON_ENV) "$(QUALITY_GATE_PYTHON)" -m bijux_canon_dev.quality.deptry_scan
DEPTRY_CONFIG ?= $(MONOREPO_ROOT)/configs/deptry.toml
QUALITY_DEPTRY_COMMAND ?= $(DEPTRY_SCAN_SCRIPT) --config "$(DEPTRY_CONFIG)" --project-dir . $(QUALITY_PATHS)
QUALITY_DEPTRY_VERSION_COMMAND ?=
PIP_AUDIT ?= env VIRTUAL_ENV= PIPAPI_PYTHON_LOCATION="$(abspath $(VENV_PYTHON))" "$(VENV_PYTHON)" -m pip_audit
SECURITY_AUDIT_PREPARE_MODE ?= pyproject
PIP_AUDIT_INPUTS ?= -r "$(SECURITY_REQS)"
SECURITY_PIP_AUDIT_TEXT_COMMAND ?= VIRTUAL_ENV= PIPAPI_PYTHON_LOCATION="$(abspath $(VENV_PYTHON))" $(CANON_DEV_PYTHON_ENV) "$(VENV_PYTHON)" -m bijux_canon_dev.security.pip_audit_gate
SBOM_VERSION_RESOLVER ?= -m bijux_canon_dev.release.version_resolver
SBOM_REQUIREMENTS_WRITER ?= -m bijux_canon_dev.sbom.requirements_writer
SBOM_PYTHON_ENV ?= $(CANON_DEV_PYTHON_ENV)

include $(ROOT_MAKE_DIR)/bijux-py/repository/env.mk
