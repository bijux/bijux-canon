# SPDX-License-Identifier: MIT

.PHONY: docs docs-serve

docs: | $(VENV)
	@echo "→ Building docs (strict)"
	@$(VENV_PYTHON) -m mkdocs build --strict --config-file "$(MKDOCS_CFG)"

docs-serve: | $(VENV)
	@$(VENV_PYTHON) -m mkdocs serve --config-file "$(MKDOCS_CFG)" -a 0.0.0.0:8000

##@ Docs
docs: ## Build MkDocs site with strict mode
docs-serve: ## Serve docs locally
