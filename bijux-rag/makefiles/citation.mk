# Citation artifacts via cffconvert (isolated env)

CFFENV           := artifacts/.cffenv
CFFENV_PY        := $(CFFENV)/bin/python
CFFCONVERT_BIN   := $(CFFENV)/bin/cffconvert

CITATION_FILE    := CITATION.cff
CITATION_DIR     := artifacts/citation
CITATION_BIB     := $(CITATION_DIR)/citation.bib
CITATION_RIS     := $(CITATION_DIR)/citation.ris
CITATION_ENDNOTE := $(CITATION_DIR)/citation.enw

.PHONY: citation citation-install citation-validate citation-bibtex citation-ris citation-endnote citation-clean-env citation-clean

citation: | $(CITATION_DIR)
	@$(MAKE) -s citation-install
	@$(MAKE) -s NO_CLEAN=1 citation-validate
	@$(MAKE) -s NO_CLEAN=1 citation-bibtex
	@$(MAKE) -s NO_CLEAN=1 citation-ris
	@$(MAKE) -s NO_CLEAN=1 citation-endnote
	@$(MAKE) -s citation-clean-env
	@echo "✔ Citation artifacts in $(CITATION_DIR)"

citation-install:
	@echo "→ Installing cffconvert (isolated env)"
	@python3 -m venv "$(CFFENV)"
	@$(CFFENV_PY) -m pip install --upgrade pip
	@$(CFFENV_PY) -m pip install --upgrade "cffconvert>=2.0"

citation-validate:
	@if [ ! -f "$(CITATION_FILE)" ]; then echo "✘ $(CITATION_FILE) missing"; exit 1; fi
	@$(CFFCONVERT_BIN) --validate --infile "$(CITATION_FILE)"
	@if [ -z "$(NO_CLEAN)" ]; then $(MAKE) -s citation-clean-env; fi

citation-bibtex: | $(CITATION_DIR)
	@$(CFFCONVERT_BIN) -f bibtex --infile "$(CITATION_FILE)" --outfile "$(CITATION_BIB)"
	@if [ -z "$(NO_CLEAN)" ]; then $(MAKE) -s citation-clean-env; fi

citation-ris: | $(CITATION_DIR)
	@$(CFFCONVERT_BIN) -f ris --infile "$(CITATION_FILE)" --outfile "$(CITATION_RIS)"
	@if [ -z "$(NO_CLEAN)" ]; then $(MAKE) -s citation-clean-env; fi

citation-endnote: | $(CITATION_DIR)
	@$(CFFCONVERT_BIN) -f endnote --infile "$(CITATION_FILE)" --outfile "$(CITATION_ENDNOTE)"
	@if [ -z "$(NO_CLEAN)" ]; then $(MAKE) -s citation-clean-env; fi

citation-clean-env:
	@rm -rf "$(CFFENV)"

citation-clean:
	@rm -rf "$(CITATION_DIR)" "$(CFFENV)"

$(CITATION_DIR):
	@mkdir -p "$(CITATION_DIR)"

##@ Citation
citation: ## Validate CITATION.cff and generate BibTeX/RIS/EndNote artifacts
