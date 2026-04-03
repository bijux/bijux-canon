# Security checks (Bandit + pip-audit)

SECURITY_PATHS       ?= src/bijux_rag
SECURITY_REPORT_DIR  ?= artifacts/security
BANDIT               := $(ACT)/bandit
PIP_AUDIT            := $(ACT)/pip-audit
SECURITY_IGNORE_IDS  ?= PYSEC-2022-42969
SECURITY_IGNORE_FLAGS = $(foreach V,$(SECURITY_IGNORE_IDS),--ignore-vuln $(V))
BANDIT_OPTS          ?= --severity-level high --confidence-level high -s B101,B311

.PHONY: security security-bandit security-audit security-clean

security: security-bandit security-audit

security-bandit:
	@mkdir -p "$(SECURITY_REPORT_DIR)"
	@echo "→ Bandit"
	@$(BANDIT) $(BANDIT_OPTS) -r "$(SECURITY_PATHS)" -x ".venv,.tox,build,dist,tests" -f json -o "$(SECURITY_REPORT_DIR)/bandit.json"
	@$(BANDIT) $(BANDIT_OPTS) -r "$(SECURITY_PATHS)" -x ".venv,.tox,build,dist,tests" 2>&1 | tee "$(SECURITY_REPORT_DIR)/bandit.txt"

security-audit:
	@mkdir -p "$(SECURITY_REPORT_DIR)"
	@echo "→ pip-audit"
	@$(PIP_AUDIT) $(SECURITY_IGNORE_FLAGS) --progress-spinner off --format json -o "$(SECURITY_REPORT_DIR)/pip-audit.json"
	@$(PIP_AUDIT) $(SECURITY_IGNORE_FLAGS) --progress-spinner off 2>&1 | tee "$(SECURITY_REPORT_DIR)/pip-audit.txt"

security-clean:
	@rm -rf "$(SECURITY_REPORT_DIR)"

##@ Security
security: ## Run Bandit + pip-audit (artifacts under artifacts/security)
security-clean: ## Remove security artifacts
