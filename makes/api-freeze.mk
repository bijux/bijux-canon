API_FREEZE_COMMAND ?= $(VENV_PYTHON) -m bijux_canon_dev.api.freeze_contracts --repo-root "$(MONOREPO_ROOT)"
API_OPENAPI_DRIFT_COMMAND ?=

include $(ROOT_MAKE_DIR)/bijux-py/api-freeze.mk
