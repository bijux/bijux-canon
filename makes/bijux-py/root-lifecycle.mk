.PHONY: install lock lock-check all root-check-env clean-root-artifacts

ROOT_INSTALL_PREREQS ?=
ROOT_INSTALL_COMMAND ?= @true
ROOT_LOCK_FLAGS ?= --python "$(PYTHON)"
ROOT_LOCK_CHECK_FLAGS ?= --check --python "$(PYTHON)"
ROOT_ALL_TARGETS ?= test lint quality security docs api build sbom
ROOT_CHECK_ENV_PREREQS ?=
ROOT_CHECK_ENV_COMMAND ?= @true
ROOT_CLEAN_ROOT_ARTIFACTS_COMMAND ?= @true

install: $(ROOT_INSTALL_PREREQS)
	$(ROOT_INSTALL_COMMAND)

lock:
	@$(UV) lock $(ROOT_LOCK_FLAGS)

lock-check:
	@$(UV) lock $(ROOT_LOCK_CHECK_FLAGS)

all: $(ROOT_ALL_TARGETS)

root-check-env: $(ROOT_CHECK_ENV_PREREQS)
	$(ROOT_CHECK_ENV_COMMAND)

clean-root-artifacts:
	$(ROOT_CLEAN_ROOT_ARTIFACTS_COMMAND)
