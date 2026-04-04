PRIMARY_PACKAGES := \
	bijux-canon-dev \
	bijux-canon-runtime \
	bijux-canon-agent \
	bijux-canon-ingest \
	bijux-canon-reason \
	bijux-canon-index

COMPAT_PACKAGES := \
	compat-agentic-flows \
	compat-bijux-agent \
	compat-bijux-rag \
	compat-bijux-rar \
	compat-bijux-vex

ALL_PACKAGES := $(PRIMARY_PACKAGES) $(COMPAT_PACKAGES)
CHECK_PACKAGES := $(ALL_PACKAGES)
PACKAGE ?=
PACKAGE_MAKE_DIR := $(CURDIR)/makes/packages

ARTIFACTS_ROOT := $(CURDIR)/artifacts
ROOT_ARTIFACTS_DIR := $(ARTIFACTS_ROOT)/root
ROOT_CHECK_VENV := $(ROOT_ARTIFACTS_DIR)/check-venv
ROOT_CHECK_PYTHON := $(ROOT_CHECK_VENV)/bin/python
ROOT_CHECK_STAMP := $(ROOT_ARTIFACTS_DIR)/.check-tools.stamp
ROOT_DOCS_ARTIFACTS_DIR := $(ROOT_ARTIFACTS_DIR)/docs
ROOT_DOCS_SITE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/site
ROOT_DOCS_CACHE_DIR := $(ROOT_DOCS_ARTIFACTS_DIR)/cache
ROOT_DOCS_SERVE_CFG := $(ROOT_DOCS_ARTIFACTS_DIR)/mkdocs.serve.yml
ROOT_DOCS_DEV_ADDR ?= 127.0.0.1:8001
ROOT_CHECK_BOOTSTRAP_PYTHON := $(shell command -v python3.11 || command -v python3)
ROOT_CHECK_PACKAGES := \
	bandit \
	codespell \
	deptry \
	interrogate \
	mkdocs \
	mkdocs-click \
	mkdocs-gen-files \
	mkdocs-git-revision-date-localized-plugin \
	mkdocs-glightbox \
	mkdocs-include-markdown-plugin \
	mkdocs-literate-nav \
	mkdocs-material \
	mkdocs-minify-plugin \
	mkdocs-redirects \
	mkdocs-section-index \
	mkdocstrings \
	mypy \
	pydantic \
	pip-audit \
	pydocstyle \
	pymdown-extensions \
	radon \
	ruff \
	types-requests \
	vulture

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX := $(ROOT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME := $(ROOT_ARTIFACTS_DIR)/xdg_cache
export HYPOTHESIS_STORAGE_DIRECTORY := $(ROOT_ARTIFACTS_DIR)/hypothesis
export PYTHONPATH := $(CURDIR)/packages/bijux-canon-dev/src$(if $(PYTHONPATH),:$(PYTHONPATH))

DEFAULT_GOAL := help
.PHONY: \
	help list list-all lint quality security test docs docs-check docs-serve api build sbom clean all \
	clean-root-artifacts root-check-env

define resolve_package
$(strip \
$(if $(filter $(1),$(ALL_PACKAGES)),$(1), \
$(if $(filter $(1),agentic-flows),bijux-canon-runtime, \
$(if $(filter $(1),bijux-agent),bijux-canon-agent, \
$(if $(filter $(1),bijux-rag),bijux-canon-ingest, \
$(if $(filter $(1),bijux-rar),bijux-canon-reason, \
$(if $(filter $(1),bijux-vex),bijux-canon-index)))))))
endef

define assert_package
	@if [ -n "$(PACKAGE)" ] && [ -z "$(call resolve_package,$(PACKAGE))" ]; then \
	  echo "Unknown package '$(PACKAGE)'."; \
	  echo "Valid package values:"; \
	  printf "  %s\n" $(ALL_PACKAGES) agentic-flows bijux-agent bijux-rag bijux-rar bijux-vex; \
	  exit 2; \
	fi
endef

define run_target
	@set -eu; \
	resolved_package="$(call resolve_package,$(PACKAGE))"; \
	if [ -n "$$resolved_package" ]; then \
	  package_list="$$resolved_package"; \
	else \
	  package_list="$(2)"; \
	fi; \
	mkdir -p "$(ROOT_ARTIFACTS_DIR)"; \
	cleanup() { $(MAKE) clean-root-artifacts >/dev/null; }; \
	trap cleanup EXIT; \
	if [ "$(3)" = "1" ]; then \
	  $(MAKE) root-check-env >/dev/null; \
	fi; \
	failures=""; \
	for package in $$package_list; do \
	  profile_path="$(PACKAGE_MAKE_DIR)/$$package.mk"; \
	  if [ ! -f "$$profile_path" ]; then \
	    echo "Missing package profile: $$profile_path"; \
	    failures="$$failures $$package"; \
	    continue; \
	  fi; \
	  echo "==> $$package: $(1)"; \
	  if [ "$(3)" = "1" ]; then \
	    if ! $(MAKE) -C "packages/$$package" -f "$$profile_path" \
	      VENV="$(ROOT_CHECK_VENV)" \
	      VENV_PYTHON="$(ROOT_CHECK_PYTHON)" \
	      PYTHON="$(ROOT_CHECK_PYTHON)" \
	      ACT="$(ROOT_CHECK_VENV)/bin" \
	      $(1); then \
	      failures="$$failures $$package"; \
	    fi; \
	  elif ! $(MAKE) -C "packages/$$package" -f "$$profile_path" $(1); then \
	    failures="$$failures $$package"; \
	  fi; \
	done; \
	if [ -n "$$failures" ]; then \
	  echo; \
	  echo "Packages with $(1) failures:$$failures"; \
	  exit 2; \
	fi
endef

help:
	@printf "%s\n" \
	  "Targets:" \
	  "  list                List primary package slugs" \
	  "  list-all            List every package slug" \
	  "  test                Run tests package by package" \
	  "  lint                Run lint package by package" \
	  "  quality             Run quality package by package" \
	  "  security            Run security package by package" \
	  "  docs                Build the monorepo docs site from root/docs" \
	  "  api                 Run API checks package by package" \
	  "  build               Build package artifacts package by package" \
	  "  sbom                Generate package SBOMs package by package" \
	  "  clean               Clean package artifacts package by package" \
	  "  clean-root-artifacts Remove stray root-level caches outside artifacts/" \
	  "  all                 Run test, lint, quality, security, docs, api, build, sbom" \
	  "" \
	  "Use PACKAGE=<slug> to scope a target to one package." \
	  "Legacy PACKAGE aliases still resolve to the canonical bijux-canon-* package names."

list:
	@printf "%s\n" $(PRIMARY_PACKAGES)

list-all:
	@printf "%s\n" $(ALL_PACKAGES)

clean-root-artifacts:
	@rm -rf \
	  "$(CURDIR)/.hypothesis" \
	  "$(CURDIR)/.pytest_cache" \
	  "$(CURDIR)/.ruff_cache" \
	  "$(CURDIR)/.mypy_cache" \
	  "$(CURDIR)/.coverage" \
	  "$(CURDIR)/.coverage."* \
	  "$(CURDIR)/.benchmarks" \
	  "$(CURDIR)/htmlcov" \
	  "$(CURDIR)/configs/.pytest_cache" \
	  "$(CURDIR)/configs/.ruff_cache" \
	  "$(CURDIR)/configs/.mypy_cache" \
	  "$(CURDIR)/configs/.hypothesis" || true

root-check-env: $(ROOT_CHECK_STAMP)

$(ROOT_CHECK_STAMP):
	@mkdir -p "$(ROOT_ARTIFACTS_DIR)"
	@rm -rf "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_BOOTSTRAP_PYTHON)" -m venv "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade pip setuptools wheel >/dev/null
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade $(ROOT_CHECK_PACKAGES) >/dev/null
	@touch "$(ROOT_CHECK_STAMP)"

test:
	$(call assert_package)
	$(call run_target,test,$(PRIMARY_PACKAGES))

lint:
	$(call assert_package)
	$(call run_target,lint,$(CHECK_PACKAGES),1)

quality:
	$(call assert_package)
	$(call run_target,quality,$(CHECK_PACKAGES),1)

security:
	$(call assert_package)
	$(call run_target,security,$(CHECK_PACKAGES),1)

docs:
	@mkdir -p "$(ROOT_DOCS_ARTIFACTS_DIR)" "$(ROOT_DOCS_CACHE_DIR)"
	@rm -rf "$(CURDIR)/site" "$(CURDIR)/.cache"
	@$(MAKE) root-check-env >/dev/null
	@echo "==> root docs"
	@XDG_CACHE_HOME="$(ROOT_DOCS_CACHE_DIR)" \
	  "$(ROOT_CHECK_PYTHON)" -m mkdocs build --strict \
	  --config-file "$(CURDIR)/mkdocs.yml" \
	  --site-dir "$(ROOT_DOCS_SITE_DIR)"
	@test ! -e "$(CURDIR)/site"
	@test ! -e "$(CURDIR)/.cache"
	@echo "Docs built in $(ROOT_DOCS_SITE_DIR)"

docs-check:
	@mkdir -p "$(ROOT_DOCS_ARTIFACTS_DIR)" "$(ROOT_DOCS_CACHE_DIR)"
	@rm -rf "$(CURDIR)/site" "$(CURDIR)/.cache"
	@$(MAKE) root-check-env >/dev/null
	@echo "==> root docs check"
	@XDG_CACHE_HOME="$(ROOT_DOCS_CACHE_DIR)" \
	  "$(ROOT_CHECK_PYTHON)" -m mkdocs build --strict --quiet \
	  --config-file "$(CURDIR)/mkdocs.yml" \
	  --site-dir "$(ROOT_DOCS_SITE_DIR)"
	@test ! -e "$(CURDIR)/site"
	@test ! -e "$(CURDIR)/.cache"
	@echo "Docs check passed"

docs-serve:
	@mkdir -p "$(ROOT_DOCS_ARTIFACTS_DIR)" "$(ROOT_DOCS_CACHE_DIR)"
	@rm -rf "$(CURDIR)/site" "$(CURDIR)/.cache"
	@$(MAKE) root-check-env >/dev/null
	@script="$(ROOT_DOCS_ARTIFACTS_DIR)/render_root_docs_serve_config.py"; \
	  printf '%s\n' \
	    'from pathlib import Path' \
	    'import os' \
	    '' \
	    'src = Path(os.environ["ROOT_DOCS_CFG"])' \
	    'dst = Path(os.environ["ROOT_DOCS_SERVE_CFG"])' \
	    'inherit_cfg = Path(os.environ["ROOT_DOCS_SHARED_CFG"]).resolve()' \
	    'site_url = "http://" + os.environ["ROOT_DOCS_DEV_ADDR"] + "/"' \
	    'docs_dir = Path(os.environ["ROOT_DOCS_SRC"]).resolve()' \
	    'site_dir = Path(os.environ["ROOT_DOCS_SITE_DIR"]).resolve()' \
	    '' \
	    'lines = src.read_text(encoding="utf-8").splitlines()' \
	    'rewritten = []' \
	    'wrote_inherit = False' \
	    'wrote_site_url = False' \
	    'wrote_docs_dir = False' \
	    'wrote_site_dir = False' \
	    'for line in lines:' \
	    '    if line.startswith("INHERIT:"):' \
	    '        rewritten.append(f"INHERIT: {inherit_cfg}")' \
	    '        wrote_inherit = True' \
	    '    elif line.startswith("site_url:"):' \
	    '        rewritten.append(f"site_url: {site_url}")' \
	    '        wrote_site_url = True' \
	    '    elif line.startswith("docs_dir:"):' \
	    '        rewritten.append(f"docs_dir: {docs_dir}")' \
	    '        wrote_docs_dir = True' \
	    '    elif line.startswith("site_dir:"):' \
	    '        rewritten.append(f"site_dir: {site_dir}")' \
	    '        wrote_site_dir = True' \
	    '    else:' \
	    '        rewritten.append(line)' \
	    'if not wrote_inherit:' \
	    '    rewritten.insert(0, f"INHERIT: {inherit_cfg}")' \
	    'if not wrote_site_url:' \
	    '    rewritten.append(f"site_url: {site_url}")' \
	    'if not wrote_docs_dir:' \
	    '    rewritten.append(f"docs_dir: {docs_dir}")' \
	    'if not wrote_site_dir:' \
	    '    rewritten.append(f"site_dir: {site_dir}")' \
	    'dst.write_text("\n".join(rewritten) + "\n", encoding="utf-8")' \
	    > "$$script"; \
	  ROOT_DOCS_CFG="$(CURDIR)/mkdocs.yml" ROOT_DOCS_SHARED_CFG="$(CURDIR)/mkdocs.shared.yml" ROOT_DOCS_SERVE_CFG="$(ROOT_DOCS_SERVE_CFG)" ROOT_DOCS_DEV_ADDR="$(ROOT_DOCS_DEV_ADDR)" ROOT_DOCS_SRC="$(CURDIR)/docs" ROOT_DOCS_SITE_DIR="$(ROOT_DOCS_SITE_DIR)" \
	    "$(ROOT_CHECK_PYTHON)" "$$script"
	@echo "==> root docs serve on http://$(ROOT_DOCS_DEV_ADDR)"
	@XDG_CACHE_HOME="$(ROOT_DOCS_CACHE_DIR)" \
	  "$(ROOT_CHECK_PYTHON)" -m mkdocs serve --strict \
	  --config-file "$(ROOT_DOCS_SERVE_CFG)" \
	  --dev-addr "$(ROOT_DOCS_DEV_ADDR)"

api:
	$(call assert_package)
	$(call run_target,api,$(PRIMARY_PACKAGES))

build:
	$(call assert_package)
	$(call run_target,build,$(PRIMARY_PACKAGES))

sbom:
	$(call assert_package)
	$(call run_target,sbom,$(PRIMARY_PACKAGES))

clean:
	$(call assert_package)
	$(call run_target,clean,$(ALL_PACKAGES))
	@$(MAKE) clean-root-artifacts

all: test lint quality security docs api build sbom
