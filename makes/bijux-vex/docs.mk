# SPDX-License-Identifier: MIT

.PHONY: docs docs-serve

docs: | $(VENV)
	@echo "→ Building docs (strict)"
	@$(VENV_PYTHON) -m mkdocs build --strict

docs-serve: | $(VENV)
	@$(VENV_PYTHON) -m mkdocs serve -a 0.0.0.0:8000

##@ Docs
docs: ## Build MkDocs site with strict mode
docs-serve: ## Serve docs locally
