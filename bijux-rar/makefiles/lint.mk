# Lint Configuration (no root cache pollution)

RUFF        := $(ACT)/ruff
MYPY        := $(ACT)/mypy
PYTYPE      := $(ACT)/pytype
CODESPELL   := $(ACT)/codespell
PYRIGHT     := $(ACT)/pyright
PYDOCSTYLE  := $(ACT)/pydocstyle
RADON       := $(ACT)/radon
MYPY_SKIP   ?= 0
PYTYPE_SKIP ?= 1

# Targets & dirs
LINT_DIRS           ?= src/bijux_rar
LINT_ARTIFACTS_DIR  ?= artifacts/lint

# Tool caches inside artifacts_pages/lint
RUFF_CACHE_DIR      ?= $(LINT_ARTIFACTS_DIR)/.ruff_cache
MYPY_CACHE_DIR      ?= $(LINT_ARTIFACTS_DIR)/.mypy_cache
PYTYPE_OUT_DIR      ?= $(LINT_ARTIFACTS_DIR)/.pytype

# In case these are not defined elsewhere
VENV_PYTHON         ?= python3
PYRIGHT_SKIP        ?= 0
PYDOCSTYLE_SKIP     ?= 1

.PHONY: lint lint-artifacts lint-file lint-dir lint-clean

lint: lint-artifacts
	@echo "✔ Linting completed (logs in '$(LINT_ARTIFACTS_DIR)')"

lint-artifacts: | $(VENV)
	@mkdir -p "$(LINT_ARTIFACTS_DIR)" "$(RUFF_CACHE_DIR)" "$(MYPY_CACHE_DIR)" "$(PYTYPE_OUT_DIR)"
	@set -euo pipefail; { \
	  echo "→ Ruff format (check)"; \
	  $(RUFF) format --check --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS); \
	} 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/ruff-format.log"
	@set -euo pipefail; $(RUFF) check --fix --config config/ruff.toml --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/ruff.log"
	@if [ "$(MYPY_SKIP)" = "1" ]; then \
	  echo "→ Skipping mypy (MYPY_SKIP=1)" | tee "$(LINT_ARTIFACTS_DIR)/mypy.log"; \
	else \
	  set -euo pipefail; $(MYPY) --version 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/mypy.log"; \
	fi
	@if [ "$(PYRIGHT_SKIP)" = "1" ]; then \
	  echo "→ Skipping pyright (PYRIGHT_SKIP=1)" | tee "$(LINT_ARTIFACTS_DIR)/pyright.log"; \
	else \
	  set -euo pipefail; $(PYRIGHT) --version 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/pyright.log"; \
	fi
	@set -euo pipefail; $(CODESPELL) -I config/bijux.dic $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/codespell.log"
	@set -euo pipefail; $(RADON) cc -s -a $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/radon.log"
	@if [ "$(PYDOCSTYLE_SKIP)" = "1" ]; then \
	  echo "→ Skipping pydocstyle (PYDOCSTYLE_SKIP=1)" | tee "$(LINT_ARTIFACTS_DIR)/pydocstyle.log"; \
	else \
	  set -euo pipefail; $(PYDOCSTYLE) --convention=google $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/pydocstyle.log"; \
	fi
	@if [ "$(PYTYPE_SKIP)" = "1" ] || $(VENV_PYTHON) -c 'import sys; sys.exit(0 if sys.version_info >= (3,13) else 1)'; then \
	  echo "Pytype skipped (PYTYPE_SKIP=1 or Python ≥3.13)" | tee "$(LINT_ARTIFACTS_DIR)/pytype.log"; \
	else \
	  set -euo pipefail; $(PYTYPE) -o "$(PYTYPE_OUT_DIR)" --keep-going --disable import-error $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/pytype.log"; \
	fi
	@[ -d .pytype ] && echo "→ removing stray .pytype" && rm -rf .pytype || true
	@[ -d .mypy_cache ] && echo "→ removing stray .mypy_cache" && rm -rf .mypy_cache || true
	@[ -d .ruff_cache ] && echo "→ removing stray .ruff_cache" && rm -rf .ruff_cache || true
	@printf "OK\n" > "$(LINT_ARTIFACTS_DIR)/_passed"

lint-file:
ifndef file
	$(error Usage: make lint-file file=path/to/file.py)
endif
	@$(call run_tool,RuffFormat,$(RUFF) format --cache-dir "$(RUFF_CACHE_DIR)")
	@$(call run_tool,Ruff,$(RUFF) check --fix --config config/ruff.toml --cache-dir "$(RUFF_CACHE_DIR)")
	@$(call run_tool,Mypy,$(MYPY) --config-file config/mypy.ini --strict --cache-dir "$(MYPY_CACHE_DIR)")
	@$(call run_tool,Codespell,$(CODESPELL) -I config/bijux.dic)
	@$(call run_tool,Pyright,$(PYRIGHT) --project config/pyrightconfig.json)
	@$(call run_tool,Radon,$(RADON) cc -s -a)
	@$(call run_tool,Pydocstyle,$(PYDOCSTYLE) --convention=google)
	@if $(VENV_PYTHON) -c 'import sys; sys.exit(0 if sys.version_info < (3,13) else 1)'; then \
	  $(call run_tool,Pytype,$(PYTYPE) -o "$(PYTYPE_OUT_DIR)" --keep-going --disable import-error); \
	else \
	  echo "→ Skipping Pytype (unsupported on Python ≥ 3.13)"; \
	fi

lint-dir:
ifndef dir
	$(error Usage: make lint-dir dir=<directory_path>)
endif
	@$(MAKE) LINT_DIRS="$(dir)" lint-artifacts

lint-clean:
	@echo "→ Cleaning lint artifacts"
	@rm -rf "$(LINT_ARTIFACTS_DIR)" .pytype .mypy_cache .ruff_cache || true
	@echo "✔ done"

##@ Lint
lint: ## Run all lint checks; save logs to artifacts_pages/lint/ (ruff/mypy/pytype caches under artifacts_pages/lint)
lint-artifacts: ## Same as 'lint' (explicit), generates logs
lint-file: ## Lint a single file (requires file=<path>)
lint-dir: ## Lint a directory (requires dir=<path>)
lint-clean: ## Remove lint artifacts_pages, including caches
