# Build artifacts (wheel/sdist) into artifacts/build

BUILD_DIR ?= artifacts/build
PY        ?= $(VENV_PYTHON)

.PHONY: build build-clean

build:
	@echo "→ Building wheel/sdist to $(BUILD_DIR)"
	@mkdir -p "$(BUILD_DIR)"
	@$(PY) -m build --outdir "$(BUILD_DIR)"
	@$(PY) -m twine check "$(BUILD_DIR)"/*
	@echo "✔ Build artifacts ready in $(BUILD_DIR)"

build-clean:
	@echo "→ Cleaning build artifacts"
	@rm -rf "$(BUILD_DIR)" dist build *.egg-info

##@ Build
build: ## Build wheel/sdist into artifacts/build and run twine check
build-clean: ## Remove build artifacts
