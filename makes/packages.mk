# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_DEFINE_VENV ?= 1
PACKAGE_DEFINE_INSTALL ?= 1
PACKAGE_DEFINE_BOOTSTRAP ?= 1
PACKAGE_DEFINE_CLEAN ?= 1
PACKAGE_DEFINE_ALL ?= 1
PACKAGE_DEFINE_HELP ?= 1

PACKAGE_NOTPARALLEL_TARGETS ?= all clean
PACKAGE_VENV_CREATE_MESSAGE ?= → Creating virtualenv with '$$(which $(PYTHON))' ...
PACKAGE_INSTALL_MESSAGE ?= → Installing dependencies...
PACKAGE_INSTALL_SPEC ?= .[dev]
PACKAGE_BOOTSTRAP_PREREQS ?= install
PACKAGE_CLEAN_MESSAGE ?= → Cleaning ($(VENV)) ...
PACKAGE_CLEAN_SOFT_MESSAGE ?= → Cleaning (artifacts, caches) ...
PACKAGE_CLEAN_PATHS ?=
PACKAGE_CLEAN_DELETE_PYCACHE ?= 1
PACKAGE_CLEAN_DELETE_PYC_FILES ?= 1
PACKAGE_ALL_TARGETS ?= clean install test lint quality security api build sbom
PACKAGE_ALL_MESSAGE ?= ✔ All targets completed
PACKAGE_HELP_WIDTH ?= 20
PACKAGE_BOOTSTRAP_TARGETS ?=
PACKAGE_INSTALL_TARGETS ?=

.NOTPARALLEL: $(PACKAGE_NOTPARALLEL_TARGETS)

ifeq ($(PACKAGE_DEFINE_VENV),1)
$(VENV):
	@echo "$(PACKAGE_VENV_CREATE_MESSAGE)"
	@$(PYTHON) -m venv "$(VENV)"
endif

ifeq ($(PACKAGE_DEFINE_INSTALL),1)
install: $(VENV)
	@echo "$(PACKAGE_INSTALL_MESSAGE)"
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(VENV_PYTHON) -m pip install -e "$(PACKAGE_INSTALL_SPEC)"
.PHONY: install
endif

ifeq ($(PACKAGE_DEFINE_BOOTSTRAP),1)
bootstrap: $(PACKAGE_BOOTSTRAP_PREREQS)
.PHONY: bootstrap
endif

ifneq ($(strip $(PACKAGE_BOOTSTRAP_TARGETS)),)
$(PACKAGE_BOOTSTRAP_TARGETS): | bootstrap
endif

ifneq ($(strip $(PACKAGE_INSTALL_TARGETS)),)
$(PACKAGE_INSTALL_TARGETS): install
endif

ifeq ($(PACKAGE_DEFINE_CLEAN),1)
clean: clean-soft
	@echo "$(PACKAGE_CLEAN_MESSAGE)"
	@$(RM) "$(VENV)"

clean-soft:
	@echo "$(PACKAGE_CLEAN_SOFT_MESSAGE)"
	@$(RM) $(PACKAGE_CLEAN_PATHS) || true
ifeq ($(PACKAGE_CLEAN_DELETE_PYCACHE),1)
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type d -name '__pycache__' -exec $(RM) {} +; \
	fi
endif
ifeq ($(PACKAGE_CLEAN_DELETE_PYC_FILES),1)
	@if [ "$(OS)" != "Windows_NT" ]; then \
	  find . -type f -name '*.pyc' -delete; \
	fi
endif
.PHONY: clean clean-soft
endif

ifeq ($(PACKAGE_DEFINE_ALL),1)
all: $(PACKAGE_ALL_TARGETS)
	@echo "$(PACKAGE_ALL_MESSAGE)"
.PHONY: all
endif

ifeq ($(PACKAGE_DEFINE_HELP),1)
help:
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^##@/ {gsub(/^##@ */,""); print "\n\033[1m" $$0 "\033[0m"; next} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-$(PACKAGE_HELP_WIDTH)s\033[0m %s\n", $$1, $$2}' \
	  $(MAKEFILE_LIST)
.PHONY: help
endif
