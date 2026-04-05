SECURITY_PATHS            ?= src
VENV_PYTHON               ?= $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV)/bin/python,python)
BANDIT                    ?= $(VENV_PYTHON) -m bandit
PIP_AUDIT                 ?= $(VENV_PYTHON) -m pip_audit
SKIP_BANDIT               ?= 0

SECURITY_REPORT_DIR       ?= $(PROJECT_ARTIFACTS_DIR)/security
BANDIT_JSON               := $(SECURITY_REPORT_DIR)/bandit.json
BANDIT_TXT                := $(SECURITY_REPORT_DIR)/bandit.txt
PIPA_JSON                 := $(SECURITY_REPORT_DIR)/pip-audit.json
PIPA_TXT                  := $(SECURITY_REPORT_DIR)/pip-audit.txt
SECURITY_REQS             ?= $(SECURITY_REPORT_DIR)/requirements.txt

SECURITY_IGNORE_IDS       ?= PYSEC-2022-42969
SECURITY_IGNORE_FLAGS      = $(foreach V,$(SECURITY_IGNORE_IDS),--ignore-vuln $(V))
PIP_AUDIT_CONSOLE_FLAGS   ?= --skip-editable --progress-spinner off
PIP_AUDIT_INPUTS          ?=
SECURITY_STRICT           ?= 1

BANDIT_EXCLUDES           ?= .venv,venv,build,dist,.tox,.mypy_cache,.pytest_cache
BANDIT_THREADS            ?= 0
SECURITY_BANDIT_SKIP_IDS  ?=
BANDIT_FLAGS              ?=
SECURITY_AUDIT_PREPARE_MODE ?= none
SECURITY_PIP_AUDIT_GATE   ?= -m bijux_canon_dev.security.pip_audit_gate
SECURITY_EXTRA_CHECKS     ?=

SECURITY_BANDIT_SKIP_FLAG := $(if $(SECURITY_BANDIT_SKIP_IDS),--skip $(SECURITY_BANDIT_SKIP_IDS),)

.PHONY: security security-bandit security-audit security-deps security-clean

security: security-bandit security-audit security-deps

security-bandit:
	@mkdir -p "$(SECURITY_REPORT_DIR)"
	@echo "→ Bandit (Python static analysis)"
	@if [ "$(SKIP_BANDIT)" = "1" ]; then \
	  echo "→ Skipping bandit" >"$(BANDIT_TXT)"; \
	else \
	  $(BANDIT) -r "$(SECURITY_PATHS)" -x "$(BANDIT_EXCLUDES)" $(SECURITY_BANDIT_SKIP_FLAG) $(BANDIT_FLAGS) -f json -o "$(BANDIT_JSON)" -n $(BANDIT_THREADS) || true; \
	  $(BANDIT) -r "$(SECURITY_PATHS)" -x "$(BANDIT_EXCLUDES)" $(SECURITY_BANDIT_SKIP_FLAG) $(BANDIT_FLAGS) -n $(BANDIT_THREADS) | tee "$(BANDIT_TXT)"; \
	fi

security-audit:
	@mkdir -p "$(SECURITY_REPORT_DIR)"
	@echo "→ Pip-audit (dependency vulnerability scan)"
	@if [ "$(SECURITY_AUDIT_PREPARE_MODE)" = "pyproject" ]; then \
	  $(VENV_PYTHON) -c "import tomllib; from pathlib import Path; data=tomllib.loads(Path('pyproject.toml').read_text()); reqs=data.get('project', {}).get('dependencies', []); Path('$(SECURITY_REQS)').write_text('\\n'.join(reqs) + '\\n')"; \
	fi
	@set -e; RC=0; \
	$(PIP_AUDIT) $(SECURITY_IGNORE_FLAGS) $(PIP_AUDIT_CONSOLE_FLAGS) $(PIP_AUDIT_INPUTS) \
	  -f json -o "$(PIPA_JSON)" >/dev/null 2>&1 || RC=$$?; \
	if [ $$RC -gt 1 ]; then \
	  echo "! pip-audit invocation failed (rc=$$RC)"; \
	  if [ "$(SECURITY_STRICT)" = "1" ]; then exit $$RC; fi; \
	fi
	@PIPA_JSON="$(PIPA_JSON)" \
	SECURITY_STRICT="$(SECURITY_STRICT)" \
	SECURITY_IGNORE_IDS="$(SECURITY_IGNORE_IDS)" \
	"$(VENV_PYTHON)" $(SECURITY_PIP_AUDIT_GATE) >"$(PIPA_TXT)"
	@cat "$(PIPA_TXT)"

security-deps:
	@if [ -n "$(SECURITY_EXTRA_CHECKS)" ]; then \
	  for script in $(SECURITY_EXTRA_CHECKS); do \
	    echo "→ Running $$script"; \
	    "$(VENV_PYTHON)" "$$script"; \
	  done; \
	fi

security-clean:
	@rm -rf "$(SECURITY_REPORT_DIR)"

##@ Security
security:        ## Run Bandit, pip-audit, and any package-specific dependency checks
security-bandit: ## Run Bandit (screen + JSON artifact)
security-audit:  ## Run pip-audit once, gate results, and write reports
security-deps:   ## Run package-specific security helper scripts when configured
security-clean:  ## Remove security reports
