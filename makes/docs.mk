DOCS_PYTHON               ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3.11)
DOCS_SITE_DIR             ?= $(PROJECT_ARTIFACTS_DIR)/docs/site
DOCS_CACHE_DIR            ?= $(PROJECT_ARTIFACTS_DIR)/docs/.cache
DOCS_DEV_ADDR             ?= 127.0.0.1:8001
DOCS_SITE_URL             ?= http://127.0.0.1:8000/
DOCS_BUILD_FLAGS          ?= --strict
DOCS_DEPLOY_FLAGS         ?= --force
DOCS_ENABLE_SOCIAL_CARDS  ?= false
DOCS_EXTRA_CLEAN_PATHS    ?=
DOCS_HYGIENE_FORBID_ROOT  ?= site .cache

ifeq ($(shell uname -s),Darwin)
  DOCS_BREW_PREFIX   := $(shell command -v brew >/dev/null 2>&1 && brew --prefix)
  DOCS_LIBFFI_PREFIX := $(shell test -n "$(DOCS_BREW_PREFIX)" && brew --prefix libffi)
  DOCS_ENV           := DYLD_FALLBACK_LIBRARY_PATH="$(DOCS_BREW_PREFIX)/lib:$(DOCS_LIBFFI_PREFIX)/lib:$$DYLD_FALLBACK_LIBRARY_PATH"
else
  DOCS_ENV           :=
endif

DOCS_GOALS := $(filter docs docs-serve docs-deploy docs-check,$(MAKECMDGOALS))
ifneq ($(strip $(DOCS_GOALS)),)
  ifeq ($(wildcard $(MKDOCS_CFG)),)
    $(error mkdocs config '$(MKDOCS_CFG)' not found)
  endif
endif

.PHONY: docs docs-serve docs-deploy docs-check docs-clean docs-hygiene

docs: docs-clean
	@echo "→ Building documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --config-file "$(MKDOCS_CFG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs built → $(DOCS_SITE_DIR)"

docs-serve:
	@echo "→ Serving documentation on http://$(DOCS_DEV_ADDR)/"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) SITE_URL="$(DOCS_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs serve --config-file "$(MKDOCS_CFG)" --dev-addr "$(DOCS_DEV_ADDR)"

docs-deploy: docs-clean
	@echo "→ Deploying documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" SITE_URL="$(DOCS_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs gh-deploy $(DOCS_BUILD_FLAGS) $(DOCS_DEPLOY_FLAGS) --config-file "$(MKDOCS_CFG)" --site-dir "$(DOCS_SITE_DIR)"

docs-check:
	@echo "→ Checking documentation build integrity"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --quiet --config-file "$(MKDOCS_CFG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs check passed"

docs-clean:
	@echo "→ Cleaning documentation artifacts"
	@rm -rf "$(DOCS_SITE_DIR)" "$(DOCS_CACHE_DIR)" $(DOCS_EXTRA_CLEAN_PATHS)

docs-hygiene:
	@set -e; \
	for path in $(DOCS_HYGIENE_FORBID_ROOT); do \
	  test ! -e "$$path" || { echo "ERROR: root '$$path' is forbidden"; exit 1; }; \
	done
	@echo "Docs hygiene OK"

##@ Docs
docs:         ## Build MkDocs site with strict settings under $(PROJECT_ARTIFACTS_DIR)/docs/site
docs-serve:   ## Serve docs locally from DOCS_DEV_ADDR
docs-deploy:  ## Deploy docs with mkdocs gh-deploy
docs-check:   ## Validate docs build without persisting root pollution
docs-clean:   ## Remove generated docs artifacts
docs-hygiene: ## Fail if forbidden root docs outputs exist
