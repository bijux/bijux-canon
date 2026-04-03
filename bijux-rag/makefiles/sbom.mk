# SBOM generation (pip-audit -> CycloneDX JSON)

PACKAGE_NAME    ?= bijux-rag
SBOM_DIR        ?= artifacts/sbom
SBOM_FORMAT     ?= cyclonedx-json
PIP_AUDIT       := $(ACT)/pip-audit
SBOM_IGNORE_IDS ?= PYSEC-2022-42969
SBOM_IGNORE_FLAGS = $(foreach V,$(SBOM_IGNORE_IDS),--ignore-vuln $(V))

SBOM_PROD_REQ   ?= requirements/prod.txt
SBOM_DEV_REQ    ?= requirements/dev.txt

.PHONY: sbom sbom-prod sbom-dev sbom-summary sbom-clean

sbom: sbom-clean sbom-prod sbom-dev sbom-summary
	@echo "✔ SBOMs ready in $(SBOM_DIR)"

sbom-prod:
	@mkdir -p "$(SBOM_DIR)"
	@if [ -s "$(SBOM_PROD_REQ)" ]; then \
	  echo "→ SBOM (prod via $(SBOM_PROD_REQ))"; \
	  $(PIP_AUDIT) --progress-spinner off --format $(SBOM_FORMAT) $(SBOM_IGNORE_FLAGS) -r "$(SBOM_PROD_REQ)" --output "$(SBOM_DIR)/$(PACKAGE_NAME)-prod.cdx.json" || true; \
	else \
	  echo "→ SBOM (prod fallback: current env)"; \
	  $(PIP_AUDIT) --progress-spinner off --format $(SBOM_FORMAT) $(SBOM_IGNORE_FLAGS) --output "$(SBOM_DIR)/$(PACKAGE_NAME)-prod.cdx.json" || true; \
	fi

sbom-dev:
	@mkdir -p "$(SBOM_DIR)"
	@if [ -s "$(SBOM_DEV_REQ)" ]; then \
	  echo "→ SBOM (dev via $(SBOM_DEV_REQ))"; \
	  $(PIP_AUDIT) --progress-spinner off --format $(SBOM_FORMAT) $(SBOM_IGNORE_FLAGS) -r "$(SBOM_DEV_REQ)" --output "$(SBOM_DIR)/$(PACKAGE_NAME)-dev.cdx.json" || true; \
	else \
	  echo "→ SBOM (dev fallback: current env)"; \
	  $(PIP_AUDIT) --progress-spinner off --format $(SBOM_FORMAT) $(SBOM_IGNORE_FLAGS) --output "$(SBOM_DIR)/$(PACKAGE_NAME)-dev.cdx.json" || true; \
	fi

sbom-summary:
	@mkdir -p "$(SBOM_DIR)"
	@summary="$(SBOM_DIR)/summary.txt"; : > "$$summary"; \
	for f in "$(SBOM_DIR)"/*.cdx.json; do \
	  [ -f "$$f" ] || continue; \
	  echo "$$(basename "$$f")" >> "$$summary"; \
	done; \
	echo "files listed in $$summary"

sbom-clean:
	@rm -rf "$(SBOM_DIR)"

##@ SBOM
sbom: ## Generate CycloneDX SBOMs (prod/dev) via pip-audit
sbom-clean: ## Remove SBOM artifacts
