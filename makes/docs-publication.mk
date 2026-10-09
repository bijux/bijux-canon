# Publication uses Canon's public identity independently of local preview defaults.
DOCS_PUBLICATION_SITE_URL ?= $(if $(filter environment command line,$(origin DOCS_BUILD_SITE_URL)),$(DOCS_BUILD_SITE_URL),https://bijux.io/bijux-canon/)
DOCS_PUBLICATION_SITE_DIR ?= $(if $(filter environment command line,$(origin DOCS_SITE_DIR)),$(DOCS_SITE_DIR),artifacts/root/docs/build-site)

.PHONY: gh-docs-install gh-docs-build gh-docs-verify

gh-docs-install: root-check-env ## Install the frozen root documentation dependencies

gh-docs-build: ## Build and qualify the exact Canon production documentation artifact
	@PYTHONDONTWRITEBYTECODE=1 $(CANON_DEV_PYTHON_ENV) "$(DOCS_PYTHON)" -m bijux_canon_dev.docs.publication build --site-url "$(DOCS_PUBLICATION_SITE_URL)" --site-dir "$(DOCS_PUBLICATION_SITE_DIR)"

gh-docs-verify: ## Recheck qualified publication bytes without rebuilding
	@PYTHONDONTWRITEBYTECODE=1 $(CANON_DEV_PYTHON_ENV) "$(DOCS_PYTHON)" -m bijux_canon_dev.docs.publication verify --site-url "$(DOCS_PUBLICATION_SITE_URL)" --site-dir "$(DOCS_PUBLICATION_SITE_DIR)"
