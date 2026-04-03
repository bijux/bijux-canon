# Changelog configuration

PYTHON      := $(shell command -v python3 || command -v python)

.PHONY: changelog changelog-check changelog-ci

changelog:
	@$(PYTHON) scripts/generate_changelog.py

changelog-check:
	@$(PYTHON) scripts/generate_changelog.py --check

changelog-ci: changelog-check
