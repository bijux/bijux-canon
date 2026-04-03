# Changelog configuration

PYTHON      := $(shell command -v python3 || command -v python)

.PHONY: changelog changelog-check changelog-version changelog-ci

changelog:
	@$(PYTHON) scripts/generate_changelog.py

changelog-check:
	@$(PYTHON) scripts/generate_changelog.py --check

changelog-version:
	@$(PYTHON) scripts/check_changelog_version.py

changelog-ci: changelog-check changelog-version
