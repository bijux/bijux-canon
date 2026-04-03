# Quality checks (dead code, deps, REUSE, doc coverage)

QUALITY_PATHS       ?= src/bijux_rag
INTERROGATE_PATHS   ?= src/bijux_rag
QUALITY_ARTIFACTS_DIR ?= artifacts/quality
QUALITY_OK_MARKER     := $(QUALITY_ARTIFACTS_DIR)/_passed

VULTURE     := $(ACT)/vulture
DEPTRY      := $(ACT)/deptry
REUSE       := $(ACT)/reuse
INTERROGATE := $(ACT)/interrogate

.PHONY: quality quality-clean interrogate-report

quality:
	@echo "→ Quality checks"
	@mkdir -p "$(QUALITY_ARTIFACTS_DIR)"
	@echo "   - Dead code (vulture)"
	@$(VULTURE) $(QUALITY_PATHS) --min-confidence 80 2>&1 | tee "$(QUALITY_ARTIFACTS_DIR)/vulture.log"
	@echo "   - Dependency hygiene (deptry)"
	@$(DEPTRY) $(QUALITY_PATHS) 2>&1 | tee "$(QUALITY_ARTIFACTS_DIR)/deptry.log"
	@echo "   - REUSE compliance"
	@$(REUSE) lint 2>&1 | tee "$(QUALITY_ARTIFACTS_DIR)/reuse.log"
	@$(MAKE) interrogate-report
	@printf "OK\n" >"$(QUALITY_OK_MARKER)"
	@echo "✔ Quality complete"

interrogate-report:
	@mkdir -p "$(QUALITY_ARTIFACTS_DIR)"
	@set +e; OUT="$$( $(INTERROGATE) --verbose $(INTERROGATE_PATHS) )"; rc=$$?; \
	printf '%s\n' "$$OUT" >"$(QUALITY_ARTIFACTS_DIR)/interrogate.full.txt"; \
	printf '%s\n' "$$OUT" | awk -F'|' 'NR>3 && $$0 ~ /^\|/ {name=$$2; cov=$$6; gsub(/^[ \t]+|[ \t]+$$/,"",name); gsub(/^[ \t]+|[ \t]+$$/,"",cov); if (name !~ /^-+$$/ && cov != "100%") printf("  - %s (%s)\n", name, cov);}' \
	  >"$(QUALITY_ARTIFACTS_DIR)/interrogate.offenders.txt"; \
	exit $$rc

quality-clean:
	@echo "→ Cleaning quality artifacts"
	@rm -rf "$(QUALITY_ARTIFACTS_DIR)"

##@ Quality
quality: ## Run vulture, deptry, reuse, interrogate (artifacts under artifacts/quality)
quality-clean: ## Remove quality artifacts
