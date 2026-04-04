INTERROGATE_PATHS         ?= src
QUALITY_PATHS             ?= $(INTERROGATE_PATHS)
QUALITY_ARTIFACTS_DIR     ?= $(PROJECT_ARTIFACTS_DIR)/quality
QUALITY_OK_MARKER         ?= $(QUALITY_ARTIFACTS_DIR)/_passed
QUALITY_MYPY_CONFIG       ?=
QUALITY_MYPY_FLAGS        ?= --strict
QUALITY_MYPY_TARGETS      ?= $(QUALITY_PATHS)
QUALITY_VULTURE_MIN_CONFIDENCE ?= 80
QUALITY_PRE_TARGETS       ?=
QUALITY_PYTHON_CHECKS     ?=
QUALITY_DOCS_LINK_SCRIPT  ?=
QUALITY_RUN_MKDOCS        ?= 0
QUALITY_MKDOCS_CONFIG     ?= $(MKDOCS_CFG)
QUALITY_CLEAN_SITE        ?= 0
QUALITY_MYPY_CACHE_DIR    ?= $(QUALITY_ARTIFACTS_DIR)/.mypy_cache

PYTHON      ?= $(shell command -v python3 || command -v python)
VULTURE     ?= $(VENV_PYTHON) -m vulture
DEPTRY      ?= $(VENV_PYTHON) -m deptry
INTERROGATE ?= $(VENV_PYTHON) -m interrogate
MYPY        ?= $(VENV_PYTHON) -m mypy
DEPTRY_SCAN_SCRIPT ?= $(VENV_PYTHON) -m bijux_canon_dev.quality.deptry_scan
DEPTRY_CONFIG ?= $(MONOREPO_ROOT)/configs/deptry.toml
QUALITY_SELF_MAKE ?= $(if $(PACKAGE_PROFILE_MAKEFILE),$(MAKE) -f "$(PACKAGE_PROFILE_MAKEFILE)",$(MAKE))

SKIP_DEPTRY      ?= 0
SKIP_INTERROGATE ?= 0
SKIP_MYPY        ?= 1

ifeq ($(shell uname -s),Darwin)
  BREW_PREFIX  := $(shell command -v brew >/dev/null 2>&1 && brew --prefix)
  CAIRO_PREFIX := $(shell test -n "$(BREW_PREFIX)" && brew --prefix cairo)
  QUALITY_ENV  := DYLD_FALLBACK_LIBRARY_PATH="$(BREW_PREFIX)/lib:$(CAIRO_PREFIX)/lib:$$DYLD_FALLBACK_LIBRARY_PATH"
else
  QUALITY_ENV  :=
endif

.PHONY: quality interrogate-report docs-links quality-clean

quality:
	@echo "→ Running quality checks..."
	@mkdir -p "$(QUALITY_ARTIFACTS_DIR)" "$(QUALITY_MYPY_CACHE_DIR)"
	@if [ "$(QUALITY_CLEAN_SITE)" = "1" ]; then rm -rf site; fi
	@for target in $(QUALITY_PRE_TARGETS); do \
	  echo "   - Running $$target"; \
	  $(QUALITY_SELF_MAKE) "$$target"; \
	done
	@echo "   - Dead code analysis (Vulture)"
	@set -euo pipefail; \
	  { $(VULTURE) --version 2>/dev/null || echo vulture; } >"$(QUALITY_ARTIFACTS_DIR)/vulture.log"; \
	  OUT="$$( $(VULTURE) $(QUALITY_PATHS) --min-confidence $(QUALITY_VULTURE_MIN_CONFIDENCE) 2>&1 || true )"; \
	  printf '%s\n' "$$OUT" >>"$(QUALITY_ARTIFACTS_DIR)/vulture.log"; \
	  if [ -z "$$OUT" ]; then echo "✔ Vulture: no dead code found." >>"$(QUALITY_ARTIFACTS_DIR)/vulture.log"; fi
	@echo "   - Dependency hygiene (Deptry)"
	@if [ "$(SKIP_DEPTRY)" = "1" ]; then \
	  echo "   • SKIP_DEPTRY=1; skipping Deptry" | tee "$(QUALITY_ARTIFACTS_DIR)/deptry.log"; \
	else \
	  set -euo pipefail; \
	    { $(DEPTRY) --version 2>/dev/null || true; } >"$(QUALITY_ARTIFACTS_DIR)/deptry.log"; \
	    $(DEPTRY_SCAN_SCRIPT) --deptry-bin "$(DEPTRY)" --config "$(DEPTRY_CONFIG)" --project-dir . $(QUALITY_PATHS) 2>&1 | tee -a "$(QUALITY_ARTIFACTS_DIR)/deptry.log"; \
	fi
	@echo "   - Static typing (Mypy)"
	@if [ "$(SKIP_MYPY)" = "1" ] || [ -z "$(QUALITY_MYPY_CONFIG)" ]; then \
	  echo "   • Skipping Mypy" | tee "$(QUALITY_ARTIFACTS_DIR)/mypy.log"; \
	else \
	  set -euo pipefail; $(MYPY) --config-file "$(QUALITY_MYPY_CONFIG)" $(QUALITY_MYPY_FLAGS) --cache-dir "$(QUALITY_MYPY_CACHE_DIR)" $(QUALITY_MYPY_TARGETS) 2>&1 | tee "$(QUALITY_ARTIFACTS_DIR)/mypy.log"; \
	fi
	@echo "   - Documentation coverage (Interrogate)"
	@if [ "$(SKIP_INTERROGATE)" = "1" ]; then \
	  echo "   • SKIP_INTERROGATE=1; skipping Interrogate" | tee "$(QUALITY_ARTIFACTS_DIR)/interrogate.full.txt"; \
	else \
	  $(QUALITY_SELF_MAKE) interrogate-report; \
	fi
	@for script in $(QUALITY_PYTHON_CHECKS); do \
	  echo "   - Running $$script"; \
	  $(PYTHON) "$$script"; \
	done
	@if [ "$(QUALITY_RUN_MKDOCS)" = "1" ]; then \
	  echo "   - MkDocs build"; \
	  $(PYTHON) -m mkdocs build --strict --config-file "$(QUALITY_MKDOCS_CONFIG)"; \
	fi
	@echo "✔ Quality checks passed"
	@printf "OK\n" >"$(QUALITY_OK_MARKER)"

interrogate-report:
	@echo "→ Generating docstring coverage report (<100%)"
	@mkdir -p "$(QUALITY_ARTIFACTS_DIR)"
	@set +e; \
	  OUT="$$( $(QUALITY_ENV) $(INTERROGATE) --fail-under 0 --verbose $(INTERROGATE_PATHS) )"; \
	  rc=$$?; \
	  printf '%s\n' "$$OUT" >"$(QUALITY_ARTIFACTS_DIR)/interrogate.full.txt"; \
	  OFF="$$(printf '%s\n' "$$OUT" | awk -F'|' 'NR>3 && $$0 ~ /^\|/ { \
	    name=$$2; cov=$$6; gsub(/^[ \\t]+|[ \\t]+$$/, "", name); gsub(/^[ \\t]+|[ \\t]+$$/, "", cov); \
	    if (name !~ /^-+$$/ && cov != "100%") printf("  - %s (%s)\n", name, cov); \
	  }')"; \
	  printf '%s\n' "$$OFF" >"$(QUALITY_ARTIFACTS_DIR)/interrogate.offenders.txt"; \
	  if [ -n "$$OFF" ]; then printf '%s\n' "$$OFF"; else echo "✔ All files 100% documented"; fi; \
	  exit $$rc

docs-links:
	@if [ -n "$(QUALITY_DOCS_LINK_SCRIPT)" ]; then \
	  $(PYTHON) "$(QUALITY_DOCS_LINK_SCRIPT)"; \
	else \
	  echo "→ docs-links is not configured for $(PROJECT_SLUG)"; \
	fi

quality-clean:
	@echo "→ Cleaning quality artifacts"
	@rm -rf "$(QUALITY_ARTIFACTS_DIR)"

##@ Quality
quality: ## Run Vulture, Deptry, Mypy, and Interrogate; save logs to $(PROJECT_ARTIFACTS_DIR)/quality
interrogate-report: ## Save full Interrogate table + offenders list
docs-links: ## Run the package docs link checker when configured
quality-clean: ## Remove quality artifacts
