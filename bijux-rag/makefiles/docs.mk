# Documentation pipeline (artifacts only)

ACT              ?= $(VENV)/bin
MKDOCS_BIN       := $(shell test -x "$(ACT)/mkdocs" && printf "%s" "$(ACT)/mkdocs" || command -v mkdocs)
MKDOCS_CFG       ?= mkdocs.yml
PY               ?= $(VENV_PYTHON)

DOCS_GEN_DIR     ?= docs
DOCS_SITE_DIR    ?= artifacts/docs/site
DOCS_CACHE_DIR   ?= artifacts/docs/.cache
DOCS_DEV_ADDR    ?= 127.0.0.1:8001

.PHONY: docs docs-serve docs-check docs-clean docs-hygiene

docs: docs-clean
	@test -x "$(MKDOCS_BIN)" || { echo "mkdocs not found; install dev extras"; exit 1; }
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" \
	  "$(MKDOCS_BIN)" build --strict --config-file "$(MKDOCS_CFG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs built → $(DOCS_SITE_DIR)"

docs-serve:
	@test -x "$(MKDOCS_BIN)" || { echo "mkdocs not found; install dev extras"; exit 1; }
	@ADDR="$(DOCS_DEV_ADDR)"; \
	echo "Serving docs at http://$$ADDR/ (override with DOCS_DEV_ADDR=host:port)"; \
	mkdir -p "$(DOCS_CACHE_DIR)"; \
	XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" \
	  "$(MKDOCS_BIN)" serve --config-file "$(MKDOCS_CFG)" --dev-addr "$$ADDR"

docs-check:
	@test -x "$(MKDOCS_BIN)" || { echo "mkdocs not found; install dev extras"; exit 1; }
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" \
	  "$(MKDOCS_BIN)" build --strict --quiet --config-file "$(MKDOCS_CFG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs check passed"

docs-clean:
	@echo "→ Cleaning docs artifacts"
	@rm -rf "$(DOCS_SITE_DIR)" "$(DOCS_CACHE_DIR)"

docs-hygiene:
	@test ! -e "site"   || (echo "ERROR: root 'site/' is forbidden"; exit 1)
	@test ! -e ".cache" || (echo "ERROR: root '.cache/' is forbidden"; exit 1)

##@ Documentation
docs: ## Build MkDocs site to artifacts/docs/site (strict)
docs-serve: ## Serve docs locally
docs-check: ## Validate docs build (strict, quiet)
docs-clean: ## Remove docs artifacts
