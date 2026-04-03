# SPDX-License-Identifier: MIT

API_ARTIFACTS_DIR ?= artifacts/api
API_LOG           ?= $(API_ARTIFACTS_DIR)/openapi_drift.log
API_SCHEMA_YAML   ?= api/v1/schema.yaml
API_SCHEMA_JSON   ?= api/v1/openapi.v1.json

.PHONY: api api-clean api-freeze

api: | $(VENV)
	@echo "→ Enforcing API schema freeze"
	@$(MAKE) api-freeze
	@echo "→ Checking API drift (if specs exist)"
	@mkdir -p "$(API_ARTIFACTS_DIR)"
	@$(VENV_PYTHON) scripts/openapi_drift.py --mode check >"$(API_LOG)" 2>&1 || true
	@echo "✔ API drift check done (log: $(API_LOG))"

api-clean:
	@rm -rf "$(API_ARTIFACTS_DIR)" || true

api-freeze: | $(VENV)
	@echo "→ Freezing API schema (yaml → json)"
	@mkdir -p "$(API_ARTIFACTS_DIR)"
	@$(VENV_PYTHON) -c "from pathlib import Path; import json, yaml; schema_yaml=Path('$(API_SCHEMA_YAML)'); tmp=Path('$(API_ARTIFACTS_DIR)')/'openapi.v1.json'; data=yaml.safe_load(schema_yaml.read_text()); tmp.write_text(json.dumps(data, indent=2))"
	@diff -u "$(API_SCHEMA_JSON)" "$(API_ARTIFACTS_DIR)/openapi.v1.json" || (echo "OpenAPI JSON drifted; regenerate and commit" && exit 1)
	@echo "✔ API schema frozen"

##@ API
api: ## Validate API schema drift (if specs are present)
api-clean: ## Remove API artifacts
api-freeze: ## Regenerate OpenAPI JSON from YAML and fail on drift
