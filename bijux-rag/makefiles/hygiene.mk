# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

SHELL := /bin/bash

.PHONY: hygiene

hygiene:
	@echo "→ Hygiene (zero-root-pollution)"
	@bad=$$(ls -1A | egrep -x '(\.coverage(\..*)?|htmlcov|\.pytest_cache|\.hypothesis|\.mypy_cache|\.ruff_cache|site|__pycache__|\.benchmarks|\.tox|\.nox)' || true); \
	if [ -n "$$bad" ]; then \
	  echo "✘ Root pollution detected:"; echo "$$bad"; exit 1; \
	fi
	@extra=$$(find . -type d -name '__pycache__' -not -path './.venv/*' -not -path './artifacts/*' -print | head -n 1); \
	if [ -n "$$extra" ]; then \
	  echo "✘ __pycache__ outside artifacts/.venv:"; echo "$$extra"; exit 1; \
	fi
	@echo "✔ hygiene OK"

##@ Hygiene
hygiene: ## Fail if caches/bytecode exist outside artifacts/.venv
