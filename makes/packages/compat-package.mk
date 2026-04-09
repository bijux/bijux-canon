PACKAGE_KIND ?= python
LINT_DIRS ?= src hatch_build.py
LINT_TARGETS ?= src hatch_build.py
MYPY_TARGETS ?= src hatch_build.py
CODESPELL_TARGETS ?= README.md hatch_build.py overview.md pyproject.toml
RADON_TARGETS ?= hatch_build.py
INTERROGATE_PATHS ?= src hatch_build.py
QUALITY_PATHS ?= src hatch_build.py
QUALITY_VULTURE_MIN_CONFIDENCE ?= 80
SECURITY_PATHS ?= src hatch_build.py
PACKAGE_INSTALL_STAMP ?= $(PROJECT_ARTIFACTS_DIR)/.compat-toolchain.stamp
PACKAGE_INSTALL_EDITABLE ?= 0
PACKAGE_INSTALL_MESSAGE ?= → Installing compatibility package toolchain...
PACKAGE_INSTALL_PYTHON_PACKAGES ?= \
  ruff mypy pydantic codespell vulture deptry interrogate bandit pip-audit \
  build twine hatchling hatch-vcs
ENABLE_MYPY ?= 1
ENABLE_CODESPELL ?= 1
ENABLE_RADON ?= 0
ENABLE_PYDOCSTYLE ?= 0
SKIP_DEPTRY ?= 0
SKIP_INTERROGATE ?= 0
SKIP_MYPY ?= 0
SKIP_BANDIT ?= 0
PUBLISH_PACKAGE_NAME ?= $(patsubst compat-%,%,$(PROJECT_SLUG))
PUBLISH_UPLOAD_ENABLED ?= 0
PACKAGE_DEFINE_BOOTSTRAP ?= 0
PACKAGE_CLEAN_PATHS ?= \
  $(COMMON_ARTIFACT_CLEAN_PATHS) $(COMMON_BUILD_CLEAN_PATHS) "$(PACKAGE_INSTALL_STAMP)"
PACKAGE_INSTALL_TARGETS ?= \
  lint-artifacts quality security-bandit security-audit security-deps \
  build publish publish-test release-dry

include $(abspath $(dir $(firstword $(MAKEFILE_LIST))))/../bijux-py/package.mk

##@ Core
clean: ## Remove virtualenv plus compatibility package artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install compatibility package toolchain
help: ## Show this help
