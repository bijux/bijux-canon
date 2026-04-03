# SPDX-License-Identifier: MIT

PACKAGE_NAME        ?= bijux-vex
GIT_SHA             ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

GIT_TAG_EXACT       := $(shell git describe --tags --exact-match 2>/dev/null | sed -E 's/^v//')
GIT_TAG_LATEST      := $(shell git describe --tags --abbrev=0 2>/dev/null | sed -E 's/^v//')

PYPROJECT_VERSION    = $(call read_pyproject_version)

PKG_VERSION         ?= $(if $(GIT_TAG_EXACT),$(GIT_TAG_EXACT),\
                           $(if $(PYPROJECT_VERSION),$(PYPROJECT_VERSION),\
                           $(if $(GIT_TAG_LATEST),$(GIT_TAG_LATEST),0.0.0)))

GIT_DESCRIBE        := $(shell git describe --tags --long --dirty --always 2>/dev/null)
PKG_VERSION_FULL    := $(if $(GIT_TAG_EXACT),$(PKG_VERSION),\
                          $(shell echo "$(GIT_DESCRIBE)" \
                            | sed -E 's/^v//; s/-([0-9]+)-g([0-9a-f]+)(-dirty)?$$/+\\1.g\\2\\3/'))

SBOM_VERSION        := $(if $(PKG_VERSION_FULL),$(PKG_VERSION_FULL),$(PKG_VERSION))

SBOM_DIR            ?= artifacts/sbom
SBOM_FORMAT         ?= cyclonedx-json
SBOM_CLI            ?= cyclonedx

PIP_AUDIT           := $(if $(ACT),$(ACT)/pip-audit,pip-audit)
PIP_AUDIT_FLAGS      = --progress-spinner off --format $(SBOM_FORMAT) --ignore PYSEC-2022-42969

SBOM_FILE           := $(SBOM_DIR)/$(PACKAGE_NAME)-$(SBOM_VERSION)-$(GIT_SHA).cdx.json

.PHONY: sbom sbom-validate sbom-summary sbom-clean

sbom: | $(VENV)
sbom: sbom-clean
	@if ! command -v $(PIP_AUDIT) >/dev/null 2>&1; then \
	  echo "→ Installing pip-audit into $(VENV)"; \
	  $(VENV_PYTHON) -m pip install --upgrade pip-audit >/dev/null; \
	fi
	@mkdir -p "$(SBOM_DIR)"
	@echo "→ SBOM from current environment → $(SBOM_FILE)"
	@$(PIP_AUDIT) $(PIP_AUDIT_FLAGS) --output "$(SBOM_FILE)" || true
	@$(MAKE) sbom-summary

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
	  for f in "$(SBOM_DIR)"/*.cdx.json; do \
	    comps=$$(jq -r '(.components|length) // 0' "$$f"); \
	    echo "$$(basename "$$f")  components=$$comps" >> "$$summary"; \
	  done; \
	fi

sbom-clean:
	@echo "→ Cleaning SBOM artifacts"
	@mkdir -p "$(SBOM_DIR)"
	@rm -f "$(SBOM_DIR)"/*.cdx.json || true

##@ SBOM
sbom:           ## Generate SBOM (pip-audit → CycloneDX JSON) and summary
sbom-validate:  ## Validate all generated SBOMs with CycloneDX CLI
sbom-summary:   ## Write a brief components summary to $(SBOM_DIR)/summary.txt
sbom-clean:     ## Remove SBOM artifacts
