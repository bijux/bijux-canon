BUILD_DIR                 ?= $(PROJECT_ARTIFACTS_DIR)/build
BUILD_PYTHON              ?= $(VENV_PYTHON)
BUILD_CHECK_DISTS         ?= 1
BUILD_REQUIRE_PYPROJECT   ?= 1
BUILD_CLEAN_PATHS         ?= build dist *.egg-info
BUILD_CLEAN_PYCACHE       ?= 0
BUILD_TEMP_CLEAN_PATHS    ?= $(BUILD_CLEAN_PATHS)
BUILD_TEMP_CLEAN_PYCACHE  ?= 0
BUILD_RELEASE_DRY_RUN_CMD ?=
BUILD_PRE_TARGETS        ?=
BUILD_POST_TARGETS       ?=
BUILD_COMMAND            ?= $(BUILD_PYTHON) -m build --wheel --sdist --outdir "$(BUILD_DIR_ABS)" .
BUILD_SDIST_COMMAND      ?= $(BUILD_PYTHON) -m build --sdist --outdir "$(BUILD_DIR_ABS)" .
BUILD_WHEEL_COMMAND      ?= $(BUILD_PYTHON) -m build --wheel --outdir "$(BUILD_DIR_ABS)" .
BUILD_SUCCESS_MESSAGE    ?= ✔ Build artifacts ready in '$(BUILD_DIR_ABS)'
BUILD_SELF_MAKE          ?= $(SELF_MAKE)

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/util.mk

BUILD_DIR_ABS             := $(abspath $(BUILD_DIR))
PYPROJECT_ABS             := $(abspath pyproject.toml)
TWINE                     ?= $(BUILD_PYTHON) -m twine

.PHONY: build build-sdist build-wheel build-check build-tools build-clean build-clean-temp release-dry

build-tools: | $(VENV)
	@echo "→ Ensuring build toolchain..."
	@$(BUILD_PYTHON) -m pip install -U pip
	@$(BUILD_PYTHON) -m pip install --upgrade build twine

build: build-tools
	@if [ "$(BUILD_REQUIRE_PYPROJECT)" = "1" ] && [ ! -f "$(PYPROJECT_ABS)" ]; then echo "✘ pyproject.toml not found"; exit 1; fi
	$(call run_make_targets,$(BUILD_PRE_TARGETS),$(BUILD_SELF_MAKE))
	@echo "→ Preparing Python package artifacts..."
	@mkdir -p "$(BUILD_DIR_ABS)"
	@echo "→ Building wheel + sdist → $(BUILD_DIR_ABS)"
	@$(BUILD_COMMAND)
	@if [ "$(BUILD_CHECK_DISTS)" = "1" ]; then \
	  echo "→ Validating distributions with twine"; \
	  $(TWINE) check "$(BUILD_DIR_ABS)"/*.whl "$(BUILD_DIR_ABS)"/*.tar.gz 2>&1 | tee "$(BUILD_DIR_ABS)/twine-check.log"; \
	else \
	  echo "→ Skipping twine check (BUILD_CHECK_DISTS=$(BUILD_CHECK_DISTS))"; \
	fi
	$(call run_make_targets,$(BUILD_POST_TARGETS),$(BUILD_SELF_MAKE))
	@echo "$(BUILD_SUCCESS_MESSAGE)"
	@ls -l "$(BUILD_DIR_ABS)" || true
	@$(BUILD_SELF_MAKE) build-clean-temp

build-sdist: build-tools
	@if [ "$(BUILD_REQUIRE_PYPROJECT)" = "1" ] && [ ! -f "$(PYPROJECT_ABS)" ]; then echo "✘ pyproject.toml not found"; exit 1; fi
	@mkdir -p "$(BUILD_DIR_ABS)"
	@echo "→ Building sdist → $(BUILD_DIR_ABS)"
	@$(BUILD_SDIST_COMMAND)
	@$(BUILD_SELF_MAKE) build-clean-temp

build-wheel: build-tools
	@if [ "$(BUILD_REQUIRE_PYPROJECT)" = "1" ] && [ ! -f "$(PYPROJECT_ABS)" ]; then echo "✘ pyproject.toml not found"; exit 1; fi
	@mkdir -p "$(BUILD_DIR_ABS)"
	@echo "→ Building wheel → $(BUILD_DIR_ABS)"
	@$(BUILD_WHEEL_COMMAND)
	@$(BUILD_SELF_MAKE) build-clean-temp

build-check:
	@if ls "$(BUILD_DIR_ABS)"/*.whl "$(BUILD_DIR_ABS)"/*.tar.gz 1>/dev/null 2>&1; then \
	  $(TWINE) check "$(BUILD_DIR_ABS)"/*.whl "$(BUILD_DIR_ABS)"/*.tar.gz 2>&1 | tee "$(BUILD_DIR_ABS)/twine-check.log"; \
	else \
	  echo "✘ No artifacts in $(BUILD_DIR_ABS) to check"; exit 1; \
	fi

build-clean-temp:
	@set -e; \
	if [ -z "$(strip $(BUILD_TEMP_CLEAN_PATHS))" ] && [ "$(BUILD_TEMP_CLEAN_PYCACHE)" != "1" ]; then \
	  echo "→ No temporary build files configured"; \
	  exit 0; \
	fi; \
	echo "→ Cleaning temporary build files"; \
	if [ -n "$(strip $(BUILD_TEMP_CLEAN_PATHS))" ]; then rm -rf $(BUILD_TEMP_CLEAN_PATHS) || true; fi; \
	if [ "$(BUILD_TEMP_CLEAN_PYCACHE)" = "1" ]; then \
	  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
	fi; \
	echo "✔ Temporary build files cleaned"

build-clean:
	@echo "→ Cleaning build artifacts..."
	@rm -rf "$(BUILD_DIR_ABS)" $(BUILD_CLEAN_PATHS) || true
	@if [ "$(BUILD_CLEAN_PYCACHE)" = "1" ]; then \
	  find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
	fi
	@$(BUILD_SELF_MAKE) build-clean-temp
	@echo "✔ Build artifacts cleaned"

release-dry: build
	@if [ -z "$(strip $(BUILD_RELEASE_DRY_RUN_CMD))" ]; then \
	  echo "→ release-dry is not configured for $(PROJECT_SLUG)"; \
	  exit 0; \
	fi
	@echo "→ Running release dry-run checks..."
	@$(BUILD_RELEASE_DRY_RUN_CMD)
	@echo "✔ Release dry-run complete"

##@ Build
build-tools:     ## Ensure the local venv has build tooling (pip, build, twine)
build-clean:     ## Remove generated build artifacts and package-specific cleanup paths
build-clean-temp: ## Remove temporary build files created during packaging
build:           ## Build wheel and sdist into $(BUILD_DIR)
build-sdist:     ## Build an sdist into $(BUILD_DIR)
build-wheel:     ## Build a wheel into $(BUILD_DIR)
build-check:     ## Run twine check on artifacts in $(BUILD_DIR)
release-dry:     ## Run package-defined release verification after building artifacts
