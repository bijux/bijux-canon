# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

COMMON_BUILD_CLEAN_PATHS := build dist *.egg-info

COMMON_PYTHON_CLEAN_PATHS := \
	.pytest_cache htmlcov coverage.xml \
	$(COMMON_BUILD_CLEAN_PATHS) \
	.tox .nox .ruff_cache .mypy_cache .hypothesis \
	.coverage.* .coverage .benchmarks .cache

COMMON_API_TEMP_CLEAN_PATHS := spec.json openapitools.json node_modules site
COMMON_ARTIFACT_CLEAN_PATHS := artifacts "$(PROJECT_ARTIFACTS_DIR)"
COMMON_CONFIG_CACHE_CLEAN_PATHS := "$(CONFIG_DIR)/.ruff_cache"
