PACKAGE_NAME              ?= $(PROJECT_SLUG)
SBOM_METADATA_PYTHON      ?= python3.11
GIT_SHA                   ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
SBOM_VERSION_RESOLVER     ?= -m bijux_canon_dev.release.version_resolver
SBOM_VERSION              ?= $(strip $(shell $(SBOM_METADATA_PYTHON) $(SBOM_VERSION_RESOLVER) --pyproject "$(SBOM_PYPROJECT)" --package-name "$(PACKAGE_NAME)" 2>/dev/null || echo 0.0.0))
SBOM_VERSION_SAFE          = $(shell printf '%s' "$(SBOM_VERSION)" | tr ' /' '__' | tr -s '_' '_')

SBOM_DIR                  ?= $(PROJECT_ARTIFACTS_DIR)/sbom
SBOM_FORMAT               ?= cyclonedx-json
SBOM_CLI                  ?= cyclonedx
SBOM_DEV_GROUP            ?= dev
SBOM_PYPROJECT            ?= pyproject.toml
SBOM_REQUIREMENTS_WRITER  ?= -m bijux_canon_dev.sbom.requirements_writer
SBOM_IGNORE_IDS           ?= PYSEC-2022-42969
SBOM_IGNORE_FLAGS          = $(foreach V,$(SBOM_IGNORE_IDS),--ignore-vuln $(V))
SBOM_PROD_REQ             := $(SBOM_DIR)/requirements.prod.txt
SBOM_DEV_REQ              := $(SBOM_DIR)/requirements.dev.txt
PIP_AUDIT                 ?= $(if $(ACT),$(ACT)/pip-audit,pip-audit)
SBOM_PIP_AUDIT_FLAGS      ?= --progress-spinner off --format $(SBOM_FORMAT)
PIP_AUDIT_FLAGS           ?= $(SBOM_PIP_AUDIT_FLAGS) $(SBOM_IGNORE_FLAGS)
SBOM_PROD_FILE             = $(SBOM_DIR)/$(PACKAGE_NAME)-$(SBOM_VERSION_SAFE)-$(GIT_SHA).prod.cdx.json
SBOM_DEV_FILE              = $(SBOM_DIR)/$(PACKAGE_NAME)-$(SBOM_VERSION_SAFE)-$(GIT_SHA).dev.cdx.json

.PHONY: sbom sbom-dev sbom-prod sbom-summary sbom-validate sbom-clean sbom-tooling

sbom: sbom-clean sbom-prod sbom-dev sbom-summary
	@echo "✔ SBOMs generated in $(SBOM_DIR)"

sbom-tooling: | $(VENV)
	@if ! command -v $(PIP_AUDIT) >/dev/null 2>&1; then \
	  echo "→ Installing pip-audit into $(VENV)"; \
	  $(UV) pip install --python "$(VENV_PYTHON)" --upgrade pip-audit >/dev/null; \
	fi

sbom-prod: sbom-tooling
	@mkdir -p "$(SBOM_DIR)"
	@$(VENV_PYTHON) $(SBOM_REQUIREMENTS_WRITER) --pyproject "$(SBOM_PYPROJECT)" --group prod --output "$(SBOM_PROD_REQ)"
	@if [ -s "$(SBOM_PROD_REQ)" ]; then \
	  echo "→ SBOM (prod via $(SBOM_PROD_REQ))"; \
	  $(PIP_AUDIT) $(PIP_AUDIT_FLAGS) -r "$(SBOM_PROD_REQ)" --output "$(SBOM_PROD_FILE)" || true; \
	else \
	  echo "→ SBOM (prod fallback: current venv)"; \
	  $(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output "$(SBOM_PROD_FILE)" || true; \
	fi

sbom-dev: sbom-tooling
	@mkdir -p "$(SBOM_DIR)"
	@$(VENV_PYTHON) $(SBOM_REQUIREMENTS_WRITER) --pyproject "$(SBOM_PYPROJECT)" --group dev --optional-group "$(SBOM_DEV_GROUP)" --output "$(SBOM_DEV_REQ)"
	@if [ -s "$(SBOM_DEV_REQ)" ]; then \
	  echo "→ SBOM (dev via $(SBOM_DEV_REQ))"; \
	  $(PIP_AUDIT) $(PIP_AUDIT_FLAGS) -r "$(SBOM_DEV_REQ)" --output "$(SBOM_DEV_FILE)" || true; \
	else \
	  echo "→ SBOM (dev fallback: current venv)"; \
	  $(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output "$(SBOM_DEV_FILE)" || true; \
	fi

sbom-validate:
	@if [ -z "$(SBOM_CLI)" ]; then echo "✘ SBOM_CLI not set"; exit 1; fi
	@command -v $(SBOM_CLI) >/dev/null 2>&1 || { echo "✘ '$(SBOM_CLI)' not found. Install it or set SBOM_CLI."; exit 1; }
	@if ! find "$(SBOM_DIR)" -maxdepth 1 -name '*.cdx.json' -print -quit | grep -q .; then \
	  echo "✘ No SBOM files in $(SBOM_DIR)"; exit 1; \
	fi
	@for f in "$(SBOM_DIR)"/*.cdx.json; do \
	  echo "→ Validating $$f"; \
	  $(SBOM_CLI) validate --input-format json --input-file "$$f"; \
	done

sbom-summary:
	@mkdir -p "$(SBOM_DIR)"
	@if ! find "$(SBOM_DIR)" -maxdepth 1 -name '*.cdx.json' -print -quit | grep -q .; then \
	  echo "→ No SBOM files found in $(SBOM_DIR); skipping summary"; \
	  exit 0; \
	fi
	@echo "→ Writing SBOM summary"
	@summary="$(SBOM_DIR)/summary.txt"; : > "$$summary"; \
	if command -v jq >/dev/null 2>&1; then \
	  find "$(SBOM_DIR)" -maxdepth 1 -name '*.cdx.json' -print0 | \
	    while IFS= read -r -d '' f; do \
	      comps=$$(jq -r '(.components|length) // 0' "$$f"); \
	      echo "$$(basename "$$f")  components=$$comps" >> "$$summary"; \
	    done; \
	else \
	  tmp="$(SBOM_DIR)/_sbom_summary.py"; \
	  echo "import glob, json, os"                                  >  "$$tmp"; \
	  echo "sbom_dir = r'$(SBOM_DIR)'"                              >> "$$tmp"; \
	  echo "for f in glob.glob(os.path.join(sbom_dir, '*.cdx.json')):" >> "$$tmp"; \
	  echo "    try:"                                               >> "$$tmp"; \
	  echo "        with open(f, 'r', encoding='utf-8') as fh:"     >> "$$tmp"; \
	  echo "            data = json.load(fh)"                       >> "$$tmp"; \
	  echo "        comps = len(data.get('components', []) or [])"  >> "$$tmp"; \
	  echo "    except Exception:"                                  >> "$$tmp"; \
	  echo "        comps = '?'"                                    >> "$$tmp"; \
	  echo "    print(os.path.basename(f) + '  components=' + str(comps))" >> "$$tmp"; \
	  python3 "$$tmp" >> "$$summary" || true; \
	  rm -f "$$tmp"; \
	fi; \
	sed -n '1,5p' "$$summary" 2>/dev/null || true

sbom-clean:
	@echo "→ Cleaning SBOM artifacts"
	@mkdir -p "$(SBOM_DIR)"
	@rm -f "$(SBOM_DIR)"/*.cdx.json "$(SBOM_DIR)"/summary.txt "$(SBOM_DIR)"/requirements.*.txt || true

##@ SBOM
sbom:           ## Generate prod/dev SBOMs from pyproject metadata and write a summary
sbom-validate:  ## Validate all generated SBOMs with CycloneDX CLI
sbom-summary:   ## Write a brief components summary to $(SBOM_DIR)/summary.txt (best-effort)
sbom-clean:     ## Remove SBOM artifacts from $(SBOM_DIR)
