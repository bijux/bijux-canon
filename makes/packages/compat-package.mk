PACKAGE_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

include $(PACKAGE_MAKEFILE_DIR)/../shared/python-package.mk

export PYTHONDONTWRITEBYTECODE := 1
export PYTHONPYCACHEPREFIX := $(PROJECT_ARTIFACTS_DIR)/pycache
export XDG_CACHE_HOME := $(PROJECT_ARTIFACTS_DIR)/xdg_cache
export COVERAGE_FILE := $(PROJECT_ARTIFACTS_DIR)/test/.coverage

LINT_DIRS := hatch_build.py
LINT_TARGETS := hatch_build.py
MYPY_TARGETS :=
CODESPELL_TARGETS := hatch_build.py overview.md pyproject.toml
RADON_TARGETS := hatch_build.py
INTERROGATE_PATHS := hatch_build.py
QUALITY_PATHS := hatch_build.py
QUALITY_VULTURE_MIN_CONFIDENCE := 80
SECURITY_PATHS := hatch_build.py
COMPAT_TOOLCHAIN_STAMP := $(PROJECT_ARTIFACTS_DIR)/.compat-toolchain.stamp
ENABLE_MYPY := 0
ENABLE_CODESPELL := 1
ENABLE_RADON := 0
ENABLE_PYDOCSTYLE := 0
SKIP_DEPTRY := 1
SKIP_INTERROGATE := 1
SKIP_MYPY := 1
SKIP_BANDIT := 0

PUBLISH_UPLOAD_ENABLED := 0

include $(ROOT_MAKE_DIR)/lint.mk
include $(ROOT_MAKE_DIR)/quality.mk
include $(ROOT_MAKE_DIR)/security.mk
include $(ROOT_MAKE_DIR)/build.mk
include $(ROOT_MAKE_DIR)/publish.mk

$(VENV):
	@echo "→ Creating virtualenv with '$$(which $(PYTHON))' ..."
	@$(PYTHON) -m venv "$(VENV)"

$(COMPAT_TOOLCHAIN_STAMP): | $(VENV)
	@echo "→ Installing compatibility package toolchain..."
	@mkdir -p "$(PROJECT_ARTIFACTS_DIR)"
	@$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(VENV_PYTHON) -m pip install --upgrade \
	  ruff codespell vulture deptry interrogate bandit pip-audit \
	  build twine hatchling hatch-vcs
	@touch "$(COMPAT_TOOLCHAIN_STAMP)"

install: $(COMPAT_TOOLCHAIN_STAMP)

lint-artifacts quality security-bandit security-audit security-deps build publish publish-test release-dry: $(COMPAT_TOOLCHAIN_STAMP)

clean:
	@echo "→ Cleaning compatibility package artifacts..."
	@$(RM) \
	  "$(VENV)" "$(PROJECT_ARTIFACTS_DIR)" build dist *.egg-info .cache \
	  "$(COMPAT_TOOLCHAIN_STAMP)" \
	  .pytest_cache .ruff_cache .mypy_cache .hypothesis .coverage .coverage.* \
	  htmlcov || true

.PHONY: clean install
