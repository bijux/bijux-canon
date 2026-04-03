# Test Configuration — zero root pollution (pytest runs from artifacts_pages/test)

TEST_PATHS            ?= tests
TEST_PATHS_UNIT       ?= tests/unit

TEST_ARTIFACTS_DIR    ?= artifacts/test
JUNIT_XML             ?= $(TEST_ARTIFACTS_DIR)/junit.xml
TMP_DIR               ?= $(TEST_ARTIFACTS_DIR)/tmp
HYPOTHESIS_DB_DIR     ?= $(TEST_ARTIFACTS_DIR)/hypothesis
BENCHMARK_DIR         ?= $(TEST_ARTIFACTS_DIR)/benchmarks

ENABLE_BENCH          ?= 1
PYTEST_ADDOPTS_EXTRA  ?=

PYTEST_PY ?= $(strip $(if $(wildcard $(VENV_PYTHON)),$(abspath $(VENV_PYTHON)),$(PYTHON)))
PYTEST ?= $(PYTEST_PY) -m pytest
PYTEST_MARKER ?= -m "not integration and not e2e"

# absolute paths so running from artifacts_pages/test works cleanly
COVCFG_ABS            := $(abspath config/coveragerc.ini)
COV_HTML_ABS          := $(abspath $(TEST_ARTIFACTS_DIR)/htmlcov)
CACHE_DIR_ABS         := $(abspath $(TEST_ARTIFACTS_DIR)/.pytest_cache)
COV_XML_ABS           := $(abspath $(TEST_ARTIFACTS_DIR)/coverage.xml)

TEST_PATHS_ABS        := $(abspath $(TEST_PATHS))
TEST_PATHS_UNIT_ABS   := $(abspath $(TEST_PATHS_UNIT))
SRC_ABS               := $(abspath src)
JUNIT_XML_ABS         := $(abspath $(JUNIT_XML))
TMP_DIR_ABS           := $(abspath $(TMP_DIR))
HYPOTHESIS_DB_ABS     := $(abspath $(HYPOTHESIS_DB_DIR))
BENCHMARK_DIR_ABS     := $(abspath $(BENCHMARK_DIR))
PYCACHE_PREFIX_ABS    := $(abspath $(TEST_ARTIFACTS_DIR)/pycache)

# override ini-relative bits with absolute paths
PYTEST_FLAGS = \
  --junitxml "$(JUNIT_XML_ABS)" \
  --basetemp "$(TMP_DIR_ABS)" \
  --cov-config "$(COVCFG_ABS)" \
  --cov-report=html:"$(COV_HTML_ABS)" \
  --cov-report=xml:"$(COV_XML_ABS)" \
  -o cache_dir="$(CACHE_DIR_ABS)" \
  $(PYTEST_ADDOPTS_EXTRA)

.PHONY: test test-unit test-clean test-syntax

test:
	@echo "→ Running full test suite on $(TEST_PATHS)"
	@$(MAKE) test-syntax
	@find . -type d -name '__pycache__' -exec rm -rf {} + >/dev/null 2>&1 || true
	@mkdir -p "$(TEST_ARTIFACTS_DIR)" "$(HYPOTHESIS_DB_DIR)" "$(BENCHMARK_DIR)" "$(TMP_DIR)"
	@rm -rf .hypothesis .benchmarks || true
	@echo "   • JUnit XML → $(JUNIT_XML_ABS)"
	@echo "   • Hypothesis DB → $(HYPOTHESIS_DB_ABS)"
	@echo "   • Using pytest → $(PYTEST)"
	@BENCH_FLAGS=""; \
	if [ "$(ENABLE_BENCH)" = "1" ] && sh -c "$(PYTEST) -q --help" 2>/dev/null | grep -q -- '--benchmark-storage'; then \
	  BENCH_FLAGS="--benchmark-autosave --benchmark-storage=file://$(BENCHMARK_DIR_ABS)"; \
	  echo "   • pytest-benchmark detected → storing in $(BENCHMARK_DIR_ABS)"; \
	else \
	  echo "   • pytest-benchmark disabled or not installed"; \
	fi; \
  ( cd "$(TEST_ARTIFACTS_DIR)" && \
  export PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPYCACHEPREFIX="$(PYCACHE_PREFIX_ABS)" \
    PYTHONPATH="$(SRC_ABS)$${PYTHONPATH:+:$${PYTHONPATH}}" \
    HYPOTHESIS_DATABASE_DIRECTORY="$(HYPOTHESIS_DB_ABS)"; \
  sh -c '$(PYTEST) $(PYTEST_MARKER) "$(TEST_PATHS_ABS)" $(PYTEST_FLAGS) '"$$BENCH_FLAGS" )
	@rm -rf .hypothesis .benchmarks || true

test-unit:
	@echo "→ Running unit tests only"
	@$(PYTEST) --version
	@echo "pytest cmd: $(PYTEST) …"
	@mkdir -p "$(TEST_ARTIFACTS_DIR)" "$(HYPOTHESIS_DB_DIR)" "$(BENCHMARK_DIR)" "$(TMP_DIR)"
	@rm -rf .hypothesis .benchmarks || true
	@echo "   • JUnit XML → $(JUNIT_XML_ABS)"
	@echo "   • Hypothesis DB → $(HYPOTHESIS_DB_ABS)"
	@echo "   • Using pytest → $(PYTEST)"
	@BENCH_FLAGS=""; \
	if [ "$(ENABLE_BENCH)" = "1" ] && sh -c "$(PYTEST) -q --help" 2>/dev/null | grep -q -- '--benchmark-storage'; then \
	  BENCH_FLAGS="--benchmark-autosave --benchmark-storage=file://$(BENCHMARK_DIR_ABS)"; \
	  echo "   • pytest-benchmark detected → storing in $(BENCHMARK_DIR_ABS)"; \
	else \
	  echo "   • pytest-benchmark disabled or not installed"; \
	fi; \
	if [ -d "$(TEST_PATHS_UNIT)" ] && find "$(TEST_PATHS_UNIT)" -type f -name 'test_*.py' | grep -q .; then \
	  echo "   • detected $(TEST_PATHS_UNIT) — targeting that directory"; \
    ( cd "$(TEST_ARTIFACTS_DIR)" && \
      export PYTHONDONTWRITEBYTECODE=1 \
        PYTHONPYCACHEPREFIX="$(PYCACHE_PREFIX_ABS)" \
        PYTHONPATH="$(SRC_ABS)$${PYTHONPATH:+:$${PYTHONPATH}}" \
        HYPOTHESIS_DATABASE_DIRECTORY="$(HYPOTHESIS_DB_ABS)"; \
      sh -c '$(PYTEST) $(PYTEST_MARKER) "$(TEST_PATHS_UNIT_ABS)" -m "not slow" --maxfail=1 -q $(PYTEST_FLAGS) '"$$BENCH_FLAGS" ); \
	else \
	  echo "   • no $(TEST_PATHS_UNIT); excluding e2e/integration/functional/slow"; \
    ( cd "$(TEST_ARTIFACTS_DIR)" && \
      export PYTHONDONTWRITEBYTECODE=1 \
        PYTHONPYCACHEPREFIX="$(PYCACHE_PREFIX_ABS)" \
        PYTHONPATH="$(SRC_ABS)$${PYTHONPATH:+:$${PYTHONPATH}}" \
        HYPOTHESIS_DATABASE_DIRECTORY="$(HYPOTHESIS_DB_ABS)"; \
      sh -c '$(PYTEST) $(PYTEST_MARKER) "$(TEST_PATHS_ABS)" -k "not e2e and not integration and not functional" -m "not slow" --maxfail=1 -q $(PYTEST_FLAGS) '"$$BENCH_FLAGS" ); \
	fi
	@rm -rf .hypothesis .benchmarks || true

test-clean:
	@echo "→ Cleaning test artifacts"
	@rm -rf ".hypothesis" ".benchmarks" || true
	@$(RM) .coverage* || true
	@echo "✔ done"

test-syntax:
	@echo "→ Running syntax-only checks (compileall src tests)"
	@mkdir -p "$(PYCACHE_PREFIX_ABS)"
	@PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$(PYCACHE_PREFIX_ABS)" $(PYTHON) -m compileall src tests

##@ Test
test: ## Run full test suite; all side-effects contained in artifacts_pages/test/ (JUnit, htmlcov, tmp, hypothesis DB, benchmarks)
test-unit: ## Run unit tests only; same containment; fallback excludes e2e/integration/functional/slow
test-clean: ## Remove stray root .hypothesis/.benchmarks and coverage files
