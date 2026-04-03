# Publish helper (local staging; no automatic upload)

PY ?= $(VENV_PYTHON)
DIST_DIR ?= artifacts/build

.PHONY: publish publish-check

publish: build publish-check
	@echo "→ Ready to upload from $(DIST_DIR); run 'twine upload $(DIST_DIR)/*' when credentials are configured."

publish-check:
	@echo "→ Twine check for built artifacts"
	@$(PY) -m twine check "$(DIST_DIR)"/*

##@ Publish
publish: ## Build artifacts and run twine check (manual upload step)
