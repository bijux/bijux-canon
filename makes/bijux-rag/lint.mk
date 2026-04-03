# Lint Configuration

RUFF        := $(ACT)/ruff
MYPY        := $(ACT)/mypy
PYTYPE      := $(ACT)/pytype

LINT_DIRS           ?= src/bijux_rag tests
MYPY_DIRS           ?= src/bijux_rag
LINT_ARTIFACTS_DIR  ?= artifacts/lint
RUFF_CACHE_DIR      ?= $(LINT_ARTIFACTS_DIR)/.ruff_cache
MYPY_CACHE_DIR      ?= $(LINT_ARTIFACTS_DIR)/.mypy_cache
PYTYPE_OUT_DIR      ?= $(LINT_ARTIFACTS_DIR)/pytype

.PHONY: lint lint-artifacts lint-clean fmt

fmt: | $(VENV)
	@mkdir -p "$(LINT_ARTIFACTS_DIR)" "$(RUFF_CACHE_DIR)"
	@set -euo pipefail; $(RUFF) format --config $(CONFIG_DIR)/ruff.toml --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS)
	@set -euo pipefail; $(RUFF) check --config $(CONFIG_DIR)/ruff.toml --fix --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS)
	@printf "OK\n" > "$(LINT_ARTIFACTS_DIR)/_fmt"

lint: lint-artifacts
	@echo "✔ Linting completed (artifacts in '$(LINT_ARTIFACTS_DIR)')"

lint-artifacts: | $(VENV)
	@mkdir -p "$(LINT_ARTIFACTS_DIR)" "$(RUFF_CACHE_DIR)" "$(MYPY_CACHE_DIR)"
	@set -euo pipefail; $(RUFF) format --config $(CONFIG_DIR)/ruff.toml --check --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/ruff-format.log"
	@set -euo pipefail; $(RUFF) check --config $(CONFIG_DIR)/ruff.toml --cache-dir "$(RUFF_CACHE_DIR)" $(LINT_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/ruff.log"
	@set -euo pipefail; $(MYPY) --config-file $(CONFIG_DIR)/mypy.ini --cache-dir "$(MYPY_CACHE_DIR)" $(MYPY_DIRS) 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/mypy.log"
	@mkdir -p "$(PYTYPE_OUT_DIR)"
	@set -euo pipefail; $(PYTYPE) --config=$(CONFIG_DIR)/pytype.cfg --output="$(PYTYPE_OUT_DIR)" src/bijux_rag/boundaries 2>&1 | tee "$(LINT_ARTIFACTS_DIR)/pytype.log"
	@[ -d .ruff_cache ] && rm -rf .ruff_cache || true
	@[ -d .mypy_cache ] && rm -rf .mypy_cache || true
	@printf "OK\n" > "$(LINT_ARTIFACTS_DIR)/_passed"

lint-clean:
	@echo "→ Cleaning lint artifacts"
	@rm -rf "$(LINT_ARTIFACTS_DIR)" .ruff_cache .mypy_cache || true
	@echo "✔ done"

##@ Lint
fmt: ## Auto-format with ruff (format + autofix)
lint: ## Run ruff + mypy + pytype (check-only, caches under artifacts/lint)
lint-clean: ## Remove lint artifacts
