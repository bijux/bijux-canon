DEPTRY_SCAN_SCRIPT ?= $(VENV_PYTHON) -m bijux_canon_dev.quality.deptry_scan
DEPTRY_CONFIG ?= $(MONOREPO_ROOT)/configs/deptry.toml
QUALITY_DEPTRY_COMMAND ?= $(DEPTRY_SCAN_SCRIPT) --deptry-bin "$(DEPTRY)" --config "$(DEPTRY_CONFIG)" --project-dir . $(QUALITY_PATHS)

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/bijux-py/quality.mk
