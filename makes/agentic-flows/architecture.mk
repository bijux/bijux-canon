# Architecture checks

PYTHON      := $(shell command -v python3 || command -v python)
PACKAGE_SCRIPTS_DIR ?= $(MONOREPO_ROOT)/scripts/agentic-flows

.PHONY: architecture-check

architecture-check:
	@$(PYTHON) "$(PACKAGE_SCRIPTS_DIR)/check_architecture_docs.py"
	@$(PYTHON) "$(PACKAGE_SCRIPTS_DIR)/check_design_debt.py"
