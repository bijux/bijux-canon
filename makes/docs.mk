DOCS_PYTHON               ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3.11)
DOCS_SITE_DIR             ?= $(PROJECT_ARTIFACTS_DIR)/docs/site
DOCS_CACHE_DIR            ?= $(PROJECT_ARTIFACTS_DIR)/docs/.cache
DOCS_SOURCE_DIR           ?= $(PROJECT_ARTIFACTS_DIR)/docs/source
DOCS_EFFECTIVE_CONFIG     ?= $(PROJECT_ARTIFACTS_DIR)/docs/mkdocs.generated.yml
DOCS_PREPARE_SCRIPT       ?= $(PROJECT_ARTIFACTS_DIR)/docs/render_mkdocs_config.py
DOCS_SHARED_ASSETS_DIR    ?= $(MONOREPO_ROOT)/docs/assets
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

.PHONY: docs docs-serve docs-deploy docs-check docs-clean docs-hygiene docs-prepare-source

docs: docs-clean docs-prepare-source
	@echo "→ Building documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --config-file "$(DOCS_EFFECTIVE_CONFIG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs built → $(DOCS_SITE_DIR)"

docs-serve: docs-prepare-source
	@echo "→ Serving documentation on http://$(DOCS_DEV_ADDR)/"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) SITE_URL="$(DOCS_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs serve --config-file "$(DOCS_EFFECTIVE_CONFIG)" --dev-addr "$(DOCS_DEV_ADDR)"

docs-deploy: docs-clean docs-prepare-source
	@echo "→ Deploying documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" SITE_URL="$(DOCS_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs gh-deploy $(DOCS_BUILD_FLAGS) $(DOCS_DEPLOY_FLAGS) --config-file "$(DOCS_EFFECTIVE_CONFIG)" --site-dir "$(DOCS_SITE_DIR)"

docs-check: docs-prepare-source
	@echo "→ Checking documentation build integrity"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --quiet --config-file "$(DOCS_EFFECTIVE_CONFIG)" --site-dir "$(DOCS_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs check passed"

docs-prepare-source:
	@echo "→ Preparing documentation source tree"
	@mkdir -p "$(DOCS_SOURCE_DIR)" "$(dir $(DOCS_EFFECTIVE_CONFIG))"
	@rm -rf "$(DOCS_SOURCE_DIR)"
	@mkdir -p "$(DOCS_SOURCE_DIR)"
	@rsync -a --delete "$(PROJECT_DIR)/docs/" "$(DOCS_SOURCE_DIR)/"
	@if [ -d "$(DOCS_SHARED_ASSETS_DIR)" ]; then \
	  mkdir -p "$(DOCS_SOURCE_DIR)/assets"; \
	  rsync -a --delete "$(DOCS_SHARED_ASSETS_DIR)/" "$(DOCS_SOURCE_DIR)/assets/"; \
	fi
	@script="$(DOCS_PREPARE_SCRIPT)"; \
	  printf '%s\n' \
	    'from pathlib import Path' \
	    'import os' \
	    '' \
	    'config_path = Path(os.environ["MKDOCS_CFG"])' \
	    'effective_path = Path(os.environ["DOCS_EFFECTIVE_CONFIG"])' \
	    'docs_source_dir = Path(os.environ["DOCS_SOURCE_DIR"]).resolve()' \
	    '' \
	    'lines = config_path.read_text(encoding="utf-8").splitlines()' \
	    'rewritten = []' \
	    'docs_dir_written = False' \
	    'for line in lines:' \
	    '    if line.startswith("docs_dir:"):' \
	    '        rewritten.append(f"docs_dir: {docs_source_dir}")' \
	    '        docs_dir_written = True' \
	    '    else:' \
	    '        rewritten.append(line)' \
	    'if not docs_dir_written:' \
	    '    rewritten.append(f"docs_dir: {docs_source_dir}")' \
	    'effective_path.write_text("\\n".join(rewritten) + "\\n", encoding="utf-8")' \
	    > "$$script"; \
	  DOCS_SOURCE_DIR="$(DOCS_SOURCE_DIR)" MKDOCS_CFG="$(MKDOCS_CFG)" DOCS_EFFECTIVE_CONFIG="$(DOCS_EFFECTIVE_CONFIG)" "$(DOCS_PYTHON)" "$$script"

docs-clean:
	@echo "→ Cleaning documentation artifacts"
	@rm -rf "$(DOCS_SITE_DIR)" "$(DOCS_CACHE_DIR)" "$(DOCS_SOURCE_DIR)" "$(DOCS_EFFECTIVE_CONFIG)" "$(DOCS_PREPARE_SCRIPT)" $(DOCS_EXTRA_CLEAN_PATHS)

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
