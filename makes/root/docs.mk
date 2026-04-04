# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PROJECT_DIR := $(CURDIR)
MKDOCS_CFG := $(CURDIR)/mkdocs.yml
DOCS_PYTHON := $(ROOT_CHECK_PYTHON)
DOCS_CACHE_DIR := $(ROOT_DOCS_CACHE_DIR)
DOCS_BUILD_SITE_DIR := $(ROOT_DOCS_BUILD_SITE_DIR)
DOCS_CHECK_SITE_DIR := $(ROOT_DOCS_CHECK_SITE_DIR)
DOCS_SERVE_SITE_DIR := $(ROOT_DOCS_SERVE_SITE_DIR)
DOCS_BUILD_CONFIG_FILE := $(CURDIR)/mkdocs.yml
DOCS_CHECK_CONFIG_FILE := $(CURDIR)/mkdocs.yml
DOCS_SERVE_CONFIG_FILE := $(ROOT_DOCS_SERVE_CFG)
DOCS_BUILD_BOOTSTRAP_TARGETS := root-check-env
DOCS_CHECK_BOOTSTRAP_TARGETS := root-check-env
DOCS_SERVE_BOOTSTRAP_TARGETS := root-check-env
DOCS_BUILD_PREPARE_TARGETS :=
DOCS_CHECK_PREPARE_TARGETS :=
DOCS_SERVE_PREPARE_TARGETS := docs-root-prepare-serve-config
DOCS_BUILD_PRE_CLEAN_PATHS := "$(ROOT_DOCS_BUILD_SITE_DIR)" "$(CURDIR)/site" "$(CURDIR)/.cache"
DOCS_CHECK_PRE_CLEAN_PATHS := "$(ROOT_DOCS_CHECK_SITE_DIR)" "$(CURDIR)/site" "$(CURDIR)/.cache"
DOCS_SERVE_PRE_CLEAN_PATHS := "$(ROOT_DOCS_SERVE_SITE_DIR)" "$(CURDIR)/site" "$(CURDIR)/.cache"
DOCS_BUILD_ENV := NO_MKDOCS_2_WARNING=true
DOCS_CHECK_ENV := NO_MKDOCS_2_WARNING=true
DOCS_SERVE_ENV := NO_MKDOCS_2_WARNING=true
DOCS_BUILD_SITE_URL := http://$(ROOT_DOCS_DEV_ADDR)/
DOCS_CHECK_SITE_URL := http://$(ROOT_DOCS_DEV_ADDR)/
DOCS_SERVE_SITE_URL := http://$(ROOT_DOCS_DEV_ADDR)/
DOCS_EXTRA_CLEAN_PATHS := "$(ROOT_DOCS_SERVE_CFG)" "$(CURDIR)/site" "$(CURDIR)/.cache"

.PHONY: docs-root-prepare-serve-config

docs-root-prepare-serve-config:
	@mkdir -p "$(ROOT_DOCS_ARTIFACTS_DIR)"
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
	    'site_dir = Path(os.environ["ROOT_DOCS_SERVE_SITE_DIR"]).resolve()' \
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
	    'dst.write_text("\\n".join(rewritten) + "\\n", encoding="utf-8")' \
	    > "$$script"; \
	  ROOT_DOCS_CFG="$(CURDIR)/mkdocs.yml" ROOT_DOCS_SHARED_CFG="$(CURDIR)/mkdocs.shared.yml" ROOT_DOCS_SERVE_CFG="$(ROOT_DOCS_SERVE_CFG)" ROOT_DOCS_DEV_ADDR="$(ROOT_DOCS_DEV_ADDR)" ROOT_DOCS_SRC="$(CURDIR)/docs" ROOT_DOCS_SERVE_SITE_DIR="$(ROOT_DOCS_SERVE_SITE_DIR)" \
	    "$(ROOT_CHECK_PYTHON)" "$$script"

include $(CURDIR)/makes/docs.mk
