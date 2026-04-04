# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

API_SCHEMA_YAML           ?= $(API_DIR)/v1/schema.yaml
API_SCHEMA_JSON           ?= $(API_DIR)/v1/pinned_openapi.json
API_DRIFT_COMMAND         ?=

.PHONY: api api-install api-freeze api-clean

api: | $(VENV)
	@echo "→ Enforcing API schema freeze"
	@$(API_SELF_MAKE) api-freeze
	@echo "→ Checking API drift (if specs exist)"
	@mkdir -p "$(API_ARTIFACTS_DIR_ABS)"
	@$(API_DRIFT_COMMAND)
	@echo "✔ API drift check done (log: $(API_LOG))"

api-install:
	@echo "→ API tooling is managed by the package install target"

api-freeze: | $(VENV)
	@echo "→ Freezing API schema (yaml → pinned json)"
	@mkdir -p "$(API_ARTIFACTS_DIR_ABS)"
	@$(VENV_PYTHON) -c "from pathlib import Path; import json, yaml; schema_yaml=Path('$(API_SCHEMA_YAML)'); tmp=Path('$(API_ARTIFACTS_DIR)')/'pinned_openapi.json'; data=yaml.safe_load(schema_yaml.read_text()); tmp.write_text(json.dumps(data, indent=2, sort_keys=True))"
	@diff -u "$(API_SCHEMA_JSON)" "$(API_ARTIFACTS_DIR)/pinned_openapi.json" || (echo "Pinned OpenAPI JSON drifted; regenerate and commit" && exit 1)
	@echo "✔ API schema frozen"

api-clean:
	@rm -rf "$(API_ARTIFACTS_DIR)" || true

##@ API
api:         ## Enforce the checked-in API freeze and run drift checks
api-install: ## Report how API tooling is provided for this package
api-freeze:  ## Regenerate OpenAPI JSON from YAML and fail on drift
api-clean:   ## Remove API artifacts
