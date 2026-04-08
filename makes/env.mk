MONOREPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
ROOT_MAKE_DIR := $(MONOREPO_ROOT)/makes
CONFIG_DIR := $(MONOREPO_ROOT)/configs/$(PROJECT_SLUG)
DOCS_CONFIG_CLI ?= -m bijux_canon_dev.docs.mkdocs_config
DEPTRY_SCAN_SCRIPT ?= $(VENV_PYTHON) -m bijux_canon_dev.quality.deptry_scan
DEPTRY_CONFIG ?= $(MONOREPO_ROOT)/configs/deptry.toml
QUALITY_DEPTRY_COMMAND ?= $(DEPTRY_SCAN_SCRIPT) --deptry-bin "$(DEPTRY)" --config "$(DEPTRY_CONFIG)" --project-dir . $(QUALITY_PATHS)
SECURITY_PIP_AUDIT_TEXT_COMMAND ?= "$(VENV_PYTHON)" -m bijux_canon_dev.security.pip_audit_gate
SBOM_VERSION_RESOLVER ?= -m bijux_canon_dev.release.version_resolver
SBOM_REQUIREMENTS_WRITER ?= -m bijux_canon_dev.sbom.requirements_writer

include $(ROOT_MAKE_DIR)/bijux-py/repository-env.mk

export PYTHONPATH := $(MONOREPO_ROOT)/packages/bijux-canon-dev/src$(if $(PYTHONPATH),:$(PYTHONPATH))
