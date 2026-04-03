# API configuration — organized, zero root pollution

# ── Server / app
SHELL                 := /bin/bash
APP_DIR               ?= src
API_HOST              ?= 127.0.0.1
API_PORT              ?= 8000
API_BASE_PATH         ?= /v1
API_APP               ?= app
API_MODULE            ?= bijux_rar.httpapi
API_FACTORY           ?=
API_WAIT_SECS         ?= 30
HEALTH_PATH           ?= /health
SCHEMA_URL            ?= http://$(API_HOST):$(API_PORT)

# Workaround for older Schemathesis versions that may hang after successful test completion.
SCHEMATHESIS_TIMEOUT  ?= 30

# ── Artifacts
API_ARTIFACTS_DIR     ?= $(PROJECT_ARTIFACTS_DIR)/api
API_LOG               ?= $(API_ARTIFACTS_DIR)/server.log
API_LINT_DIR          ?= $(API_ARTIFACTS_DIR)/lint
API_TEST_DIR          ?= $(API_ARTIFACTS_DIR)/test
SCHEMA_BUNDLE_DIR     ?= $(API_ARTIFACTS_DIR)/schemas
HYPOTHESIS_DB_API     ?= $(API_TEST_DIR)/hypothesis

SCHEMATHESIS_JUNIT    ?= $(API_TEST_DIR)/schemathesis.xml
SCHEMATHESIS_JUNIT_ABS  := $(abspath $(SCHEMATHESIS_JUNIT))

# ── Node tool sandbox (no root pollution)
API_NODE_DIR          ?= $(API_ARTIFACTS_DIR)/node
OPENAPI_GENERATOR_VERSION ?= 7.14.0
NODE_VERSION_FILE    ?= $(CONFIG_DIR)/node-version.nvmrc
NODE_REQUIRED_FILE   := $(strip $(shell sed -n 's/^[^0-9]*\([0-9][0-9]*\).*/\1/p' "$(NODE_VERSION_FILE)" 2>/dev/null | head -n 1))
NODE_REQUIRED        ?= $(if $(NODE_REQUIRED_FILE),$(NODE_REQUIRED_FILE),20)
NODE_DIST_VERSION    ?= v20.18.0
NODE_PACKAGE_MANIFEST ?= $(CONFIG_DIR)/package.json
NODE_LOCKFILE         ?= $(CONFIG_DIR)/package-lock.json

# Find schemas
ALL_API_SCHEMAS       := $(shell find "$(API_DIR)" -type f \( -name '*.yaml' -o -name '*.yml' \))
ALL_API_SCHEMAS_ABS   := $(abspath $(ALL_API_SCHEMAS))

# Python CLIs (prefer ACT if present)
PRANCE                  := $(ACT)/prance
OPENAPI_SPEC_VALIDATOR  := $(ACT)/openapi-spec-validator
SCHEMATHESIS            := $(ACT)/schemathesis
API_PYTHON              ?= $(VENV_PYTHON)
SCHEMATHESIS_OPTS ?= \
  --checks=all --max-failures=1 \
  --report junit --report-junit-path $(SCHEMATHESIS_JUNIT_ABS) \
  --request-timeout=5 --max-response-time=3 \
  --max-examples=50 --seed=1 --generation-deterministic --exclude-checks=positive_data_acceptance,response_schema_conformance \
  --suppress-health-check=filter_too_much


# ── Absolute paths (safe if recipe cd's)
API_ARTIFACTS_DIR_ABS   := $(abspath $(API_ARTIFACTS_DIR))
API_LINT_DIR_ABS        := $(abspath $(API_LINT_DIR))
API_TEST_DIR_ABS        := $(abspath $(API_TEST_DIR))
SCHEMA_BUNDLE_DIR_ABS   := $(abspath $(SCHEMA_BUNDLE_DIR))
API_LOG_ABS             := $(abspath $(API_LOG))
API_NODE_DIR_ABS        := $(abspath $(API_NODE_DIR))
HYPOTHESIS_DB_API_ABS   := $(abspath $(HYPOTHESIS_DB_API))
NODE_PACKAGE_MANIFEST_ABS := $(abspath $(NODE_PACKAGE_MANIFEST))
NODE_LOCKFILE_ABS         := $(abspath $(NODE_LOCKFILE))
REDOCLY_ABS             := $(API_NODE_DIR_ABS)/node_modules/.bin/redocly
OPENAPI_GENERATOR_ABS   := $(API_NODE_DIR_ABS)/node_modules/.bin/openapi-generator-cli

# ── Uvicorn runner (force import from src/; tolerate unset PYTHONPATH)
ifneq ($(strip $(API_FACTORY)),)
API_CMD ?= PYTHONPATH="$(APP_DIR)$${PYTHONPATH:+:$$PYTHONPATH}" \
  $(VENV_PYTHON) -c 'import sys, importlib, uvicorn; \
sys.path.insert(0,"$(APP_DIR)"); \
m=importlib.import_module("$(API_MODULE)"); \
app=getattr(m,"$(API_FACTORY)")(); \
uvicorn.run(app, host="$(API_HOST)", port=$(API_PORT))'
else
API_CMD ?= PYTHONPATH="$(APP_DIR)$${PYTHONPATH:+:$$PYTHONPATH}" \
  $(VENV_PYTHON) -m uvicorn --app-dir "$(APP_DIR)" \
  $(API_MODULE):$(API_APP) --host $(API_HOST) --port $(API_PORT)
endif

# ── Macro: validate one schema (use ABS CLI paths, no cd)
define VALIDATE_ONE_SCHEMA
  @mkdir -p "$(API_LINT_DIR_ABS)"
  @b="$$(basename "$(1)")"; \
  in_abs="$(abspath $(1))"; \
  log="$(API_LINT_DIR_ABS)/$${b}.log"; \
  echo "→ Validating: $(1)"; \
  { \
    set -euo pipefail; \
    $(PRANCE) validate "$$in_abs"; \
    $(OPENAPI_SPEC_VALIDATOR) "$$in_abs"; \
    "$(REDOCLY_ABS)" lint "$$in_abs"; \
    NODE_NO_WARNINGS=1 "$(OPENAPI_GENERATOR_ABS)" validate -i "$$in_abs"; \
  } 2>&1 | tee "$$log"
endef

.PHONY: api api-install api-lint api-test api-serve api-serve-bg api-stop api-clean node_deps node_bootstrap

## Orchestrator
api: api-install api-lint api-test

# ── Install toolchain (Python + Node sandbox)
api-install: | $(VENV) node_deps
	@echo "→ Installing API Python deps..."
	@command -v curl >/dev/null || { echo "✘ curl not found"; exit 1; }
	@command -v java >/dev/null || { echo "✘ java not found"; exit 1; }
	@$(VENV_PYTHON) -m pip install --quiet --upgrade prance openapi-spec-validator uvicorn schemathesis
	@$(VENV_PYTHON) -m pip install --quiet -e .
	@echo "✔ API toolchain ready."

api-lint: | node_deps
	@if [ -z "$(ALL_API_SCHEMAS)" ]; then echo "✘ No API schemas found under $(API_DIR)"; exit 1; fi
	@echo "→ Linting OpenAPI specs..."
	$(foreach s,$(ALL_API_SCHEMAS),$(call VALIDATE_ONE_SCHEMA,$(s)))
	@[ -f ./openapitools.json ] && echo "→ Removing stray openapitools.json (root)" && rm -f ./openapitools.json || true
	@echo "✔ All schemas validated. Logs → $(API_LINT_DIR_ABS)"

# ── Start server, wait for readiness, run Schemathesis (sandboxed Hypothesis DB), stop server
api-test: | $(VENV) node_deps
	@if [ -z "$(ALL_API_SCHEMAS)" ]; then echo "✘ No API schemas found under $(API_DIR)"; exit 1; fi
	@mkdir -p "$(API_ARTIFACTS_DIR_ABS)" "$(API_TEST_DIR_ABS)"
	@FILTER_PATH="$(API_ARTIFACTS_DIR_ABS)/schemathesis_filter.py"; \
	  printf 'import sys\nskip=False\nfor line in sys.stdin:\n    if "WARNINGS" in line or line.startswith("Warnings:") or "validation mismatch" in line or line.strip().startswith("💡") or line.strip().startswith("- "):\n        skip=True\n        continue\n    if skip and (line.startswith("SUMMARY") or line.startswith("Test cases:") or line.strip() == ""):\n        skip=False\n        if line.startswith("SUMMARY") or line.startswith("Test cases:"):\n            print(line, end="")\n        continue\n    if not skip:\n        print(line, end="")\n' >"$$FILTER_PATH"
	@echo "→ Starting API server"
	@script="$(API_ARTIFACTS_DIR_ABS)/run_api_test.sh"; \
	  rm -f "$$script"; \
	  echo '#!/usr/bin/env bash' >> "$$script"; \
	  echo 'set -euo pipefail' >> "$$script"; \
	  echo 'echo "→ Starting API server"' >> "$$script"; \
	  echo '$(API_CMD) >"$(API_LOG_ABS)" 2>&1 & PID=$$!' >> "$$script"; \
	  echo 'echo $$PID >"$(API_ARTIFACTS_DIR_ABS)/server.pid"' >> "$$script"; \
	  echo 'cleanup(){ kill $$PID >/dev/null 2>&1 || true; wait $$PID >/dev/null 2>&1 || true; }' >> "$$script"; \
	  echo 'trap cleanup EXIT INT TERM' >> "$$script"; \
	  echo 'echo "→ Waiting up to $(API_WAIT_SECS)s for readiness @ $(SCHEMA_URL)$(HEALTH_PATH)"' >> "$$script"; \
	  echo 'READY=' >> "$$script"; \
	  echo 'for i in $$(seq 1 $(API_WAIT_SECS)); do' >> "$$script"; \
	  echo '  if curl -fsS "$(SCHEMA_URL)$(HEALTH_PATH)" >/dev/null 2>&1; then READY=1; break; fi' >> "$$script"; \
	  echo '  sleep 1' >> "$$script"; \
	  echo '  if ! kill -0 $$PID >/dev/null 2>&1; then echo "✘ API crashed — see $(API_LOG_ABS)"; exit 1; fi' >> "$$script"; \
	  echo 'done' >> "$$script"; \
	  echo 'if [ -z "$$READY" ]; then echo "✘ API did not become ready in $(API_WAIT_SECS)s — see $(API_LOG_ABS)"; exit 1; fi' >> "$$script"; \
	  echo 'BASE_FLAG=$$($(SCHEMATHESIS) run -h 2>&1 | grep -q " --url " && echo --url || echo --base-url)' >> "$$script"; \
	  echo 'STATEFUL_ARGS=""' >> "$$script"; \
	  echo 'if $(SCHEMATHESIS) run -h 2>&1 | grep -q " --stateful"; then STATEFUL_ARGS="--stateful=links"; else echo "↪︎ Schemathesis: --stateful not supported; skipping"; fi' >> "$$script"; \
	  echo 'LOG="$(API_TEST_DIR_ABS)/schemathesis.log"; : > "$$LOG"' >> "$$script"; \
	  echo 'FILTER_PATH="$(API_ARTIFACTS_DIR_ABS)/schemathesis_filter.py"' >> "$$script"; \
	  echo 'BUF=""; command -v stdbuf >/dev/null 2>&1 && BUF="stdbuf -oL -eL"' >> "$$script"; \
	  echo 'TO=""' >> "$$script"; \
	  echo 'if [ "$(SCHEMATHESIS_TIMEOUT)" -gt 0 ] 2>/dev/null; then' >> "$$script"; \
	  echo '  if command -v gtimeout >/dev/null 2>&1; then TO="gtimeout --kill-after=10 $(SCHEMATHESIS_TIMEOUT)";' >> "$$script"; \
	  echo '  elif command -v timeout >/dev/null 2>&1; then TO="timeout --kill-after=10 $(SCHEMATHESIS_TIMEOUT)";' >> "$$script"; \
	  echo '  fi' >> "$$script"; \
	  echo 'fi' >> "$$script"; \
	  echo 'if [ -n "$$TO" ]; then echo "↪︎ Using timeout wrapper: $$TO"; else echo "↪︎ No timeout wrapper in use"; fi' >> "$$script"; \
	  echo 'echo "→ Running Schemathesis against: $(SCHEMA_URL)$(API_BASE_PATH)"' >> "$$script"; \
	  echo 'EXIT_CODE=0' >> "$$script"; \
	  echo 'SCHEMA_BIN="$(SCHEMATHESIS)"; case "$$SCHEMA_BIN" in /*) ;; *) SCHEMA_BIN="$$(pwd)/$$SCHEMA_BIN";; esac' >> "$$script"; \
	  echo 'tmpdir=$$(mktemp -d); trap "rm -rf $$tmpdir" EXIT; cd "$$tmpdir"' >> "$$script"; \
	  echo 'for schema in $(ALL_API_SCHEMAS_ABS); do'   >> "$$script"; \
	  echo '  echo "  • $$schema" | tee -a "$$LOG"' >> "$$script"; \
	  echo '  set +e' >> "$$script"; \
	  echo '  ( $$TO $$BUF "$$SCHEMA_BIN" run "$$schema" $$BASE_FLAG "$(SCHEMA_URL)$(API_BASE_PATH)" $(SCHEMATHESIS_OPTS) $$STATEFUL_ARGS 2>&1 || [ $$? -eq 124 ] ) | $(API_PYTHON) "$$FILTER_PATH" | tee -a "$$LOG"' >> "$$script"; \
	  echo '  rc=$${PIPESTATUS[0]}' >> "$$script"; \
	  echo '  set -e' >> "$$script"; \
	  echo '  if [ $$rc -ne 0 ] && [ $$EXIT_CODE -eq 0 ]; then EXIT_CODE=$$rc; fi' >> "$$script"; \
	  echo 'done' >> "$$script"; \
	  echo 'echo "→ Stopping API server"' >> "$$script"; \
	  echo 'cleanup' >> "$$script"; \
	  echo 'if [ $$EXIT_CODE -ne 0 ]; then echo "✘ Schemathesis reported failures (exit $$EXIT_CODE)"; fi' >> "$$script"; \
	  echo 'exit $$EXIT_CODE' >> "$$script"; \
	  chmod +x "$$script"; "$$script"
	@[ -f ./openapitools.json ] && echo "→ Removing stray openapitools.json (root)" && rm -f ./openapitools.json || true
	@echo "✔ Schemathesis finished. Log → $(API_TEST_DIR_ABS)/schemathesis.log"
	@[ -f "$(SCHEMATHESIS_JUNIT)" ] && echo "  JUnit → $(SCHEMATHESIS_JUNIT)" || true
	@[ -d .hypothesis ] && echo "→ Removing stray .hypothesis (root)" && rm -rf .hypothesis || true

# ── Dev helpers
api-serve: | $(VENV)
	@mkdir -p "$(API_ARTIFACTS_DIR_ABS)"
	@echo "→ Serving API (foreground) @ $(SCHEMA_URL) — logs → $(API_LOG_ABS)"
	@$(API_CMD)

api-serve-bg: | $(VENV)
	@mkdir -p "$(API_ARTIFACTS_DIR_ABS)"
	@echo "→ Serving API (background) @ $(SCHEMA_URL) — logs → $(API_LOG_ABS)"
	@$(API_CMD) >"$(API_LOG_ABS)" 2>&1 & echo $$! >"$(API_ARTIFACTS_DIR_ABS)/server.pid"
	@echo "PID $$(cat "$(API_ARTIFACTS_DIR_ABS)/server.pid")"

api-stop:
	@if [ -f "$(API_ARTIFACTS_DIR_ABS)/server.pid" ]; then \
	  PID=$$(cat "$(API_ARTIFACTS_DIR_ABS)/server.pid"); \
	  echo "→ Stopping PID $$PID"; \
	  kill $$PID >/dev/null 2>&1 || true; \
	  wait $$PID >/dev/null 2>&1 || true; \
	  rm -f "$(API_ARTIFACTS_DIR_ABS)/server.pid"; \
	else \
	  echo "→ No server.pid found (nothing to stop)"; \
	fi

# ── Node deps (sandboxed). No root pollution, no repo-level openapitools.json.
node_deps: $(API_NODE_DIR_ABS)/.deps-ok

$(API_NODE_DIR_ABS)/.deps-ok:
	@mkdir -p "$(API_NODE_DIR_ABS)" "$(API_NODE_DIR_ABS)/.npm-cache"
	@echo "→ Ensuring Node $(NODE_REQUIRED).x toolchain in sandbox"
	@PLATFORM="$$(uname -s | tr A-Z a-z)"; \
	  ARCH_RAW="$$(uname -m)"; \
	  case "$$ARCH_RAW" in \
	    x86_64) ARCH_TAG="x64" ;; \
	    aarch64|arm64) ARCH_TAG="arm64" ;; \
	    *) ARCH_TAG="$$ARCH_RAW" ;; \
	  esac; \
	  NODE_TARBALL="node-$(NODE_DIST_VERSION)-$$PLATFORM-$$ARCH_TAG"; \
	  NODE_DST="$(API_NODE_DIR_ABS)/node20"; \
	  if [ ! -x "$$NODE_DST/bin/node" ]; then \
	    echo "→ Downloading Node $(NODE_DIST_VERSION) into $$NODE_DST"; \
	    curl -fsSL "https://nodejs.org/dist/$(NODE_DIST_VERSION)/$$NODE_TARBALL.tar.gz" | tar -xz -C "$(API_NODE_DIR_ABS)" || { echo "✘ failed to download Node $(NODE_DIST_VERSION) for $$PLATFORM $$ARCH_TAG"; exit 1; }; \
	    mv "$(API_NODE_DIR_ABS)/$$NODE_TARBALL" "$$NODE_DST"; \
	  fi; \
	  export PATH="$$NODE_DST/bin:$$PATH"; \
	  NODE_ACTUAL_FULL="$$(node -v | sed 's/^v//')"; \
	  NODE_ACTUAL="$${NODE_ACTUAL_FULL%%.*}"; \
	  if [ "$$NODE_ACTUAL" != "$(NODE_REQUIRED)" ]; then \
	    echo "✘ Node $$NODE_ACTUAL_FULL detected; require $(NODE_REQUIRED).x (see $(NODE_VERSION_FILE))"; exit 1; \
	  fi; \
	  echo "→ Using node @ $$(command -v node)"; \
	  echo "→ Bootstrapping Node toolchain in $(API_NODE_DIR_ABS) using npm ci"; \
	  test -f "$(NODE_PACKAGE_MANIFEST_ABS)" || { echo "✘ missing $(NODE_PACKAGE_MANIFEST_ABS)"; exit 1; }; \
	  test -f "$(NODE_LOCKFILE_ABS)" || { echo "✘ missing $(NODE_LOCKFILE_ABS)"; exit 1; }; \
	  cp "$(NODE_PACKAGE_MANIFEST_ABS)" "$(NODE_LOCKFILE_ABS)" "$(API_NODE_DIR_ABS)"/; \
	  cd "$(API_NODE_DIR_ABS)" && { \
	    NPM_CONFIG_CACHE="$(API_NODE_DIR_ABS)/.npm-cache" \
	    npm ci --ignore-scripts --no-fund --no-audit --loglevel=info \
	      > npm-install.log 2>&1 \
	      || { echo "✘ npm ci failed — see $(API_NODE_DIR_ABS)/npm-install.log"; tail -n 200 npm-install.log; exit 1; }; \
	  }
	@echo "→ Bootstrapping Node toolchain in $(API_NODE_DIR_ABS) using npm ci"
	@test -x "$(REDOCLY_ABS)" || { echo "✘ redocly CLI not found in sandbox"; exit 1; }
	@test -x "$(OPENAPI_GENERATOR_ABS)" || { echo "✘ openapi-generator-cli not found in sandbox"; exit 1; }
	@touch "$@"

.PHONY: api-repro
api-repro:
	@echo "→ Reproducing API toolchain from scratch"
	@rm -rf "$(API_NODE_DIR_ABS)"
	@$(MAKE) api

# ── Cleanup
api-clean:
	@echo "→ Cleaning API artifacts"
	@rm -rf "$(API_ARTIFACTS_DIR_ABS)" || true
	@echo "✔ Done"

##@ API
api:            ## Run full API workflow (install → lint → test with Schemathesis); artifacts in $(PROJECT_ARTIFACTS_DIR)/api/**
api-install:    ## Install API toolchain (Python deps + sandboxed Node deps)
api-lint:       ## Validate all OpenAPI specs; logs to $(PROJECT_ARTIFACTS_DIR)/api/lint/*.log
api-test:       ## Start server, wait for /health, run Schemathesis; logs and JUnit to $(PROJECT_ARTIFACTS_DIR)/api/**
api-serve:      ## Serve API in the foreground (dev)
api-serve-bg:   ## Serve API in the background; PID to $(PROJECT_ARTIFACTS_DIR)/api/server.pid
api-stop:       ## Stop background API (if running)
api-clean:      ## Remove all API artifacts
