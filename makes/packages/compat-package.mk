include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk
include $(ROOT_MAKE_DIR)/package/canon-compat-package.mk

include $(ROOT_MAKE_DIR)/bijux-py/lint.mk
include $(ROOT_MAKE_DIR)/bijux-py/quality.mk
include $(ROOT_MAKE_DIR)/bijux-py/security.mk
include $(ROOT_MAKE_DIR)/bijux-py/build.mk
include $(ROOT_MAKE_DIR)/publish.mk

include $(PACKAGE_MAKEFILE_DIR)/../packages.mk

##@ Core
clean: ## Remove virtualenv plus compatibility package artifacts
clean-soft: ## Remove build artifacts but keep .venv
install: ## Install compatibility package toolchain
help: ## Show this help
