DOCS_PYTHON               ?= $(if $(wildcard $(VENV_PYTHON)),$(VENV_PYTHON),python3.11)
DOCS_SITE_DIR             ?= $(PROJECT_ARTIFACTS_DIR)/docs/site
DOCS_BUILD_SITE_DIR       ?= $(DOCS_SITE_DIR)
DOCS_CHECK_SITE_DIR       ?= $(DOCS_SITE_DIR)
DOCS_SERVE_SITE_DIR       ?= $(DOCS_SITE_DIR)
DOCS_CACHE_DIR            ?= $(PROJECT_ARTIFACTS_DIR)/docs/.cache
DOCS_SOURCE_DIR           ?= $(PROJECT_ARTIFACTS_DIR)/docs/source
DOCS_EFFECTIVE_CONFIG     ?= $(PROJECT_ARTIFACTS_DIR)/docs/mkdocs.generated.yml
DOCS_BUILD_CONFIG_FILE    ?= $(DOCS_EFFECTIVE_CONFIG)
DOCS_CHECK_CONFIG_FILE    ?= $(DOCS_EFFECTIVE_CONFIG)
DOCS_SERVE_CONFIG_FILE    ?= $(DOCS_EFFECTIVE_CONFIG)
DOCS_PREPARE_SCRIPT       ?= $(PROJECT_ARTIFACTS_DIR)/docs/render_mkdocs_config.py
DOCS_SHARED_ASSETS_DIR    ?= $(MONOREPO_ROOT)/docs/assets
DOCS_DEV_ADDR             ?= 127.0.0.1:8001
DOCS_SITE_URL             ?= http://127.0.0.1:8000/
DOCS_BUILD_SITE_URL       ?= $(DOCS_SITE_URL)
DOCS_CHECK_SITE_URL       ?= $(DOCS_SITE_URL)
DOCS_SERVE_SITE_URL       ?= $(DOCS_SITE_URL)
DOCS_BUILD_FLAGS          ?= --strict
DOCS_SERVE_FLAGS          ?=
DOCS_DEPLOY_FLAGS         ?= --force
DOCS_ENABLE_SOCIAL_CARDS  ?= false
DOCS_EXTRA_CLEAN_PATHS    ?=
DOCS_HYGIENE_FORBID_ROOT  ?= site .cache
DOCS_BUILD_BOOTSTRAP_TARGETS ?=
DOCS_CHECK_BOOTSTRAP_TARGETS ?=
DOCS_SERVE_BOOTSTRAP_TARGETS ?=
DOCS_BUILD_PREPARE_TARGETS ?= docs-prepare-source
DOCS_CHECK_PREPARE_TARGETS ?= docs-prepare-source
DOCS_SERVE_PREPARE_TARGETS ?= docs-prepare-source
DOCS_SERVE_GUARD_TARGETS ?=
DOCS_BUILD_PRE_CLEAN_PATHS ?=
DOCS_CHECK_PRE_CLEAN_PATHS ?=
DOCS_SERVE_PRE_CLEAN_PATHS ?=
DOCS_BUILD_ENV           ?=
DOCS_CHECK_ENV           ?=
DOCS_SERVE_ENV           ?=
DOCS_SERVE_REUSE_MATCH   ?= $(DOCS_SERVE_CONFIG_FILE)
DOCS_SERVE_STATUS_FILE   ?= $(DOCS_CACHE_DIR)/.serve-state
DOCS_RENDER_SERVE_CONFIG ?= 0
DOCS_BASE_CONFIG_FILE    ?= $(MKDOCS_CFG)
DOCS_SHARED_CONFIG_FILE  ?=
DOCS_RENDERED_DOCS_DIR   ?= $(PROJECT_DIR)/docs

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

.PHONY: docs docs-serve docs-serve-run docs-deploy docs-check docs-clean docs-hygiene docs-prepare-source docs-assert-serve-port docs-render-serve-config

define run_docs_targets
	@if [ -n "$(strip $(1))" ]; then \
	  for target in $(1); do \
	    echo "→ Running $$target"; \
	    $(MAKE) "$$target"; \
	  done; \
	fi
endef

define clean_docs_paths
	@if [ -n "$(strip $(1))" ]; then \
	  rm -rf $(1); \
	fi
endef

docs:
	$(call run_docs_targets,$(DOCS_BUILD_BOOTSTRAP_TARGETS))
	$(call clean_docs_paths,$(DOCS_BUILD_PRE_CLEAN_PATHS))
	$(call run_docs_targets,$(DOCS_BUILD_PREPARE_TARGETS))
	@echo "→ Building documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) $(DOCS_BUILD_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" SITE_URL="$(DOCS_BUILD_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --config-file "$(DOCS_BUILD_CONFIG_FILE)" --site-dir "$(DOCS_BUILD_SITE_DIR)"
	@$(MAKE) docs-hygiene
	@echo "✔ Docs built → $(DOCS_BUILD_SITE_DIR)"

docs-serve:
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@status_file="$(DOCS_SERVE_STATUS_FILE)"; \
	rm -f "$$status_file"; \
	set -eu; \
	addr="$(DOCS_DEV_ADDR)"; \
	port="$${addr##*:}"; \
	if lsof_output="$$(lsof -nP -iTCP:$$port -sTCP:LISTEN 2>/dev/null)"; then \
	  pid="$$(printf '%s\n' "$$lsof_output" | awk 'NR==2 {print $$2}')"; \
	  command_line="$$(ps -p "$$pid" -o command= 2>/dev/null || true)"; \
	  if [ -n "$(DOCS_SERVE_REUSE_MATCH)" ] && printf '%s\n' "$$command_line" | grep -Fq -- "$(DOCS_SERVE_REUSE_MATCH)"; then \
	    echo "→ Documentation already serving on http://$$addr (pid $$pid)"; \
	    echo reuse > "$$status_file"; \
	    exit 0; \
	  fi; \
	  echo "Port $$addr is already in use by pid $$pid."; \
	  if [ -n "$$command_line" ]; then \
	    echo "$$command_line"; \
	  fi; \
	  echo "Stop that process or set DOCS_DEV_ADDR to a free port."; \
	  exit 2; \
	fi; \
	echo proceed > "$$status_file"
	@if [ "$$(cat "$(DOCS_SERVE_STATUS_FILE)" 2>/dev/null || true)" = "reuse" ]; then \
	  exit 0; \
	else \
	  $(MAKE) docs-serve-run; \
	fi

docs-serve-run:
	$(call run_docs_targets,$(DOCS_SERVE_BOOTSTRAP_TARGETS))
	$(call clean_docs_paths,$(DOCS_SERVE_PRE_CLEAN_PATHS))
	$(call run_docs_targets,$(DOCS_SERVE_PREPARE_TARGETS))
	@echo "→ Serving documentation on http://$(DOCS_DEV_ADDR)/"
	@exec env XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) $(DOCS_SERVE_ENV) SITE_URL="$(DOCS_SERVE_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs serve $(DOCS_SERVE_FLAGS) --config-file "$(DOCS_SERVE_CONFIG_FILE)" --dev-addr "$(DOCS_DEV_ADDR)"

docs-deploy:
	$(call run_docs_targets,$(DOCS_BUILD_BOOTSTRAP_TARGETS))
	$(call clean_docs_paths,$(DOCS_BUILD_PRE_CLEAN_PATHS))
	$(call run_docs_targets,$(DOCS_BUILD_PREPARE_TARGETS))
	@echo "→ Deploying documentation"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) $(DOCS_BUILD_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" SITE_URL="$(DOCS_BUILD_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs gh-deploy $(DOCS_BUILD_FLAGS) $(DOCS_DEPLOY_FLAGS) --config-file "$(DOCS_BUILD_CONFIG_FILE)" --site-dir "$(DOCS_BUILD_SITE_DIR)"

docs-check:
	$(call run_docs_targets,$(DOCS_CHECK_BOOTSTRAP_TARGETS))
	$(call clean_docs_paths,$(DOCS_CHECK_PRE_CLEAN_PATHS))
	$(call run_docs_targets,$(DOCS_CHECK_PREPARE_TARGETS))
	@echo "→ Checking documentation build integrity"
	@mkdir -p "$(DOCS_CACHE_DIR)"
	@XDG_CACHE_HOME="$(DOCS_CACHE_DIR)" $(DOCS_ENV) $(DOCS_CHECK_ENV) ENABLE_SOCIAL_CARDS="$(DOCS_ENABLE_SOCIAL_CARDS)" SITE_URL="$(DOCS_CHECK_SITE_URL)" \
	  "$(DOCS_PYTHON)" -m mkdocs build $(DOCS_BUILD_FLAGS) --quiet --config-file "$(DOCS_CHECK_CONFIG_FILE)" --site-dir "$(DOCS_CHECK_SITE_DIR)"
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
	    'effective_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")' \
	    > "$$script"; \
	  DOCS_SOURCE_DIR="$(DOCS_SOURCE_DIR)" MKDOCS_CFG="$(MKDOCS_CFG)" DOCS_EFFECTIVE_CONFIG="$(DOCS_EFFECTIVE_CONFIG)" "$(DOCS_PYTHON)" "$$script"

docs-clean:
	@echo "→ Cleaning documentation artifacts"
	@rm -rf \
	  "$(DOCS_SITE_DIR)" \
	  "$(DOCS_BUILD_SITE_DIR)" \
	  "$(DOCS_CHECK_SITE_DIR)" \
	  "$(DOCS_SERVE_SITE_DIR)" \
	  "$(DOCS_CACHE_DIR)" \
	  "$(DOCS_SOURCE_DIR)" \
	  "$(DOCS_EFFECTIVE_CONFIG)" \
	  "$(DOCS_PREPARE_SCRIPT)" \
	  $(DOCS_EXTRA_CLEAN_PATHS)

docs-hygiene:
	@set -e; \
	for path in $(DOCS_HYGIENE_FORBID_ROOT); do \
	  test ! -e "$$path" || { echo "ERROR: root '$$path' is forbidden"; exit 1; }; \
	done
	@echo "Docs hygiene OK"

docs-assert-serve-port:
	@set -eu; \
	addr="$(DOCS_DEV_ADDR)"; \
	port="$${addr##*:}"; \
	if lsof_output="$$(lsof -nP -iTCP:$$port -sTCP:LISTEN 2>/dev/null)"; then \
	  pid="$$(printf '%s\n' "$$lsof_output" | awk 'NR==2 {print $$2}')"; \
	  command_line="$$(ps -p "$$pid" -o command= 2>/dev/null || true)"; \
	  if [ -n "$(DOCS_SERVE_REUSE_MATCH)" ] && printf '%s\n' "$$command_line" | grep -Fq -- "$(DOCS_SERVE_REUSE_MATCH)"; then \
	    echo "→ Documentation already serving on http://$$addr (pid $$pid)"; \
	    exit 0; \
	  fi; \
	  echo "Port $$addr is already in use by pid $$pid."; \
	  if [ -n "$$command_line" ]; then \
	    echo "$$command_line"; \
	  fi; \
	  echo "Stop that process or set DOCS_DEV_ADDR to a free port."; \
	  exit 2; \
	fi

docs-render-serve-config:
	@if [ "$(DOCS_RENDER_SERVE_CONFIG)" != "1" ]; then \
	  echo "→ Serve config rendering is not enabled for this docs profile"; \
	  exit 0; \
	fi
	@mkdir -p "$(dir $(DOCS_SERVE_CONFIG_FILE))"
	@script="$(DOCS_CACHE_DIR)/render_docs_serve_config.py"; \
	  mkdir -p "$(DOCS_CACHE_DIR)"; \
	  printf '%s\n' \
	    'from pathlib import Path' \
	    'import os' \
	    '' \
	    'src = Path(os.environ["DOCS_BASE_CONFIG_FILE"])' \
	    'dst = Path(os.environ["DOCS_SERVE_CONFIG_FILE"])' \
	    'inherit_cfg = os.environ.get("DOCS_SHARED_CONFIG_FILE", "").strip()' \
	    'site_url = os.environ["DOCS_SERVE_SITE_URL"]' \
	    'docs_dir = Path(os.environ["DOCS_RENDERED_DOCS_DIR"]).resolve()' \
	    'site_dir = Path(os.environ["DOCS_SERVE_SITE_DIR"]).resolve()' \
	    '' \
	    'lines = src.read_text(encoding="utf-8").splitlines()' \
	    'rewritten = []' \
	    'wrote_inherit = False' \
	    'wrote_site_url = False' \
	    'wrote_docs_dir = False' \
	    'wrote_site_dir = False' \
	    'for line in lines:' \
	    '    if line.startswith("INHERIT:") and inherit_cfg:' \
	    '        rewritten.append(f"INHERIT: {Path(inherit_cfg).resolve()}")' \
	    '        wrote_inherit = True' \
	    '    elif line.startswith("site_url:"):' \
	    '        rewritten.append(f"site_url: {site_url}")' \
	    '        wrote_site_url = True' \
	    '    elif line.startswith("docs_dir:"):' \
	    '        rewritten.append(f"docs_dir: {docs_dir}")' \
	    '        wrote_docs_dir = True' \
	    '    elif line.startswith("site_dir:"):' \
	    '        rewritten.append(f"site_dir: {site_dir}")' \
	    '        wrote_site_dir = True' \
	    '    else:' \
	    '        rewritten.append(line)' \
	    'if inherit_cfg and not wrote_inherit:' \
	    '    rewritten.insert(0, f"INHERIT: {Path(inherit_cfg).resolve()}")' \
	    'if not wrote_site_url:' \
	    '    rewritten.append(f"site_url: {site_url}")' \
	    'if not wrote_docs_dir:' \
	    '    rewritten.append(f"docs_dir: {docs_dir}")' \
	    'if not wrote_site_dir:' \
	    '    rewritten.append(f"site_dir: {site_dir}")' \
	    'dst.write_text("\n".join(rewritten) + "\n", encoding="utf-8")' \
	    > "$$script"; \
	  DOCS_BASE_CONFIG_FILE="$(DOCS_BASE_CONFIG_FILE)" \
	  DOCS_SHARED_CONFIG_FILE="$(DOCS_SHARED_CONFIG_FILE)" \
	  DOCS_SERVE_CONFIG_FILE="$(DOCS_SERVE_CONFIG_FILE)" \
	  DOCS_SERVE_SITE_URL="$(DOCS_SERVE_SITE_URL)" \
	  DOCS_RENDERED_DOCS_DIR="$(DOCS_RENDERED_DOCS_DIR)" \
	  DOCS_SERVE_SITE_DIR="$(DOCS_SERVE_SITE_DIR)" \
	  "$(DOCS_PYTHON)" "$$script"

##@ Docs
docs:         ## Build MkDocs site with strict settings under $(PROJECT_ARTIFACTS_DIR)/docs/site
docs-serve:   ## Serve docs locally from DOCS_DEV_ADDR
docs-deploy:  ## Deploy docs with mkdocs gh-deploy
docs-check:   ## Validate docs build without persisting root pollution
docs-clean:   ## Remove generated docs artifacts
docs-hygiene: ## Fail if forbidden root docs outputs exist
