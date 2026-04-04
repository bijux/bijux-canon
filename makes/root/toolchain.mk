# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

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

root-check-env: $(ROOT_CHECK_STAMP)

$(ROOT_CHECK_STAMP):
	@mkdir -p "$(ROOT_ARTIFACTS_DIR)"
	@rm -rf "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_BOOTSTRAP_PYTHON)" -m venv "$(ROOT_CHECK_VENV)"
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade pip setuptools wheel >/dev/null
	@"$(ROOT_CHECK_PYTHON)" -m pip install --upgrade $(ROOT_CHECK_PACKAGES) >/dev/null
	@touch "$(ROOT_CHECK_STAMP)"

##@ Repository
root-check-env: ## Create or refresh the shared root check environment
