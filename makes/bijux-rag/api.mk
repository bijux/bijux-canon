# API validation (OpenAPI) — artifacts only

SHELL                 := /bin/bash
API_ARTIFACTS_DIR     ?= artifacts/api
API_LINT_DIR          ?= $(API_ARTIFACTS_DIR)/lint
API_SCHEMA            ?= api/v1/schema.yaml
API_SERVER_LOG        ?= $(API_ARTIFACTS_DIR)/server.log
API_HOST              ?= 127.0.0.1
API_PORT              ?= 8000
API_DRIFT_OUT         ?= $(API_ARTIFACTS_DIR)/openapi.generated.json

PRANCE                ?= $(ACT)/prance
OPENAPI_SPEC_VALIDATOR ?= $(ACT)/openapi-spec-validator
SCHEMATHESIS          ?= $(ACT)/schemathesis
UVICORN               ?= $(ACT)/uvicorn

.PHONY: api api-lint api-test api-clean api-drift

api: api-lint api-drift api-test

api-lint:
	@if [ ! -f "$(API_SCHEMA)" ]; then echo "✘ Missing $(API_SCHEMA)"; exit 1; fi
	@mkdir -p "$(API_LINT_DIR)"
	@echo "→ Validating OpenAPI schema $(API_SCHEMA)"
	@$(PRANCE) validate "$(API_SCHEMA)" 2>&1 | tee "$(API_LINT_DIR)/prance.log"
	@$(OPENAPI_SPEC_VALIDATOR) "$(API_SCHEMA)" 2>&1 | tee "$(API_LINT_DIR)/spec-validator.log"
	@echo "✔ API lint complete"

api-test:
	@if [ ! -x "$(UVICORN)" ]; then echo "uvicorn not found; install dev extras"; exit 1; fi
	@mkdir -p "$(API_ARTIFACTS_DIR)"
	@API_HOST="$(API_HOST)" API_PORT="$(API_PORT)" $(VENV_PYTHON) -c $$'import os, socket\nhost = os.environ.get(\"API_HOST\", \"127.0.0.1\")\npreferred = int(os.environ.get(\"API_PORT\", \"8000\"))\nbusy = False\nwith socket.socket() as sock:\n    try:\n        sock.bind((host, preferred))\n        port = preferred\n    except OSError:\n        busy = True\n        sock.bind((host, 0))\n        port = sock.getsockname()[1]\nprint(port)\nprint(int(busy))' >"$(API_ARTIFACTS_DIR)/port.meta"
	@set -euo pipefail; \
	  PORT="$$(sed -n '1p' "$(API_ARTIFACTS_DIR)/port.meta")"; \
	  FALLBACK="$$(sed -n '2p' "$(API_ARTIFACTS_DIR)/port.meta")"; \
	  if [ "$$FALLBACK" -eq 1 ]; then echo "→ Port $(API_PORT) busy; using $$PORT"; fi; \
	  echo "$$PORT" >"$(API_ARTIFACTS_DIR)/port"; \
	  echo "→ Starting API server for schemathesis on $$PORT"; \
	  $(UVICORN) bijux_rag.boundaries.web.fastapi_app:create_app --host $(API_HOST) --port $$PORT --factory >"$(API_SERVER_LOG)" 2>&1 & echo $$! >"$(API_ARTIFACTS_DIR)/server.pid"; \
	  sleep 2; \
	  echo "→ Running schemathesis against live server"
	@set -euo pipefail; \
	  BASE_FLAG=$$($(SCHEMATHESIS) run -h 2>&1 | grep -q " --url " && echo --url || echo --base-url); \
	  EXTRA_FLAG=$$(PYTHONPATH=""; "$(VENV_PYTHON)" -c "import yaml; v=yaml.safe_load(open('$(API_SCHEMA)', 'r', encoding='utf-8')).get('openapi',''); print('--experimental=openapi-3.1' if str(v).startswith('3.1') else '')"); \
	  PORT="$$(cat "$(API_ARTIFACTS_DIR)/port")"; \
	  $(SCHEMATHESIS) run "$(API_SCHEMA)" $$BASE_FLAG "http://$(API_HOST):$$PORT" $$EXTRA_FLAG --workers=1 --max-failures=1 --checks=not_a_server_error,response_schema_conformance,content_type_conformance,response_headers_conformance --hypothesis-max-examples=5 --request-timeout=30000 --max-response-time=500 --hypothesis-suppress-health-check=filter_too_much 2>&1 | tee "$(API_ARTIFACTS_DIR)/schemathesis.log"; \
	  RC=$$?; \
	  kill $$(cat "$(API_ARTIFACTS_DIR)/server.pid") >/dev/null 2>&1 || true; \
	  wait $$(cat "$(API_ARTIFACTS_DIR)/server.pid") >/dev/null 2>&1 || true; \
	  exit $$RC

api-drift:
	@mkdir -p "$(API_ARTIFACTS_DIR)"
	@echo "→ Checking OpenAPI drift"
	@$(VENV_PYTHON) scripts/openapi_drift.py --schema "$(API_SCHEMA)" --out "$(API_DRIFT_OUT)"

api-clean:
	@rm -rf "$(API_ARTIFACTS_DIR)" api/v1/__pycache__

##@ API
api: ## Lint OpenAPI schema and run schemathesis against live FastAPI server
api-lint: ## Validate OpenAPI schema with prance + openapi-spec-validator
api-drift: ## Compare generated OpenAPI from FastAPI app to checked-in schema
api-test: ## Start local API server and run schemathesis smoke
api-clean: ## Remove API artifacts
