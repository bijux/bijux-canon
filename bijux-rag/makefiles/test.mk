# Test Configuration

TEST_PATHS          ?= tests
TEST_ARTIFACTS_DIR  ?= artifacts/test
JUNIT_XML           ?= $(TEST_ARTIFACTS_DIR)/junit.xml
TMP_DIR             ?= $(TEST_ARTIFACTS_DIR)/tmp
HYPOTHESIS_DB_DIR   ?= $(TEST_ARTIFACTS_DIR)/hypothesis
COV_XML             ?= $(TEST_ARTIFACTS_DIR)/coverage.xml

PY                  ?= $(VENV_PYTHON)
PYTEST              ?= $(ACT)/pytest

PYTEST_INI_ABS      := $(abspath pytest.ini)
SRC_ABS             := $(abspath src)
TEST_PATHS_ABS      := $(abspath $(TEST_PATHS))
JUNIT_XML_ABS       := $(abspath $(JUNIT_XML))
TMP_DIR_ABS         := $(abspath $(TMP_DIR))
HYPOTHESIS_DB_ABS   := $(abspath $(HYPOTHESIS_DB_DIR))
COV_XML_ABS         := $(abspath $(COV_XML))

PYTEST_FLAGS = \
  --junitxml "$(JUNIT_XML_ABS)" \
  --basetemp "$(TMP_DIR_ABS)" \
  --cov-report=xml:"$(COV_XML_ABS)"

.PHONY: test test-clean

test:
	@echo "→ Running test suite on $(TEST_PATHS)"
	@rm -rf .hypothesis .pytest_cache .benchmarks || true
	@mkdir -p "$(TEST_ARTIFACTS_DIR)" "$(HYPOTHESIS_DB_DIR)" "$(TMP_DIR)"
	@HYPOTHESIS_DATABASE_DIRECTORY="$(HYPOTHESIS_DB_ABS)" \
	PYTHONPATH="$(SRC_ABS)$${PYTHONPATH:+:$${PYTHONPATH}}" \
	$(PYTEST) -c "$(PYTEST_INI_ABS)" "$(TEST_PATHS_ABS)" $(PYTEST_FLAGS)
	@echo "✔ tests complete (artifacts in $(TEST_ARTIFACTS_DIR))"

test-clean:
	@echo "→ Cleaning test artifacts"
	@rm -rf "$(TEST_ARTIFACTS_DIR)" .hypothesis .benchmarks .pytest_cache || true
	@echo "✔ done"

##@ Test
test: ## Run full test suite (artifacts stored under artifacts/test)
test-clean: ## Remove test artifacts and caches
