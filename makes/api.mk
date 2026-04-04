# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

API_MODE                    ?= contract
API_ARTIFACTS_DIR           ?= $(PROJECT_ARTIFACTS_DIR)/api
API_LINT_DIR                ?= $(API_ARTIFACTS_DIR)/lint
API_TEST_DIR                ?= $(API_ARTIFACTS_DIR)/test
API_LOG                     ?= $(API_ARTIFACTS_DIR)/server.log
API_HOST                    ?= 127.0.0.1
API_PORT                    ?= 8000
API_ARTIFACTS_DIR_ABS       := $(abspath $(API_ARTIFACTS_DIR))
API_LINT_DIR_ABS            := $(abspath $(API_LINT_DIR))
API_TEST_DIR_ABS            := $(abspath $(API_TEST_DIR))
API_MAKEFILE_DIR            := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
API_SELF_MAKE               ?= $(SELF_MAKE)

ifeq ($(API_MODE),contract)
include $(API_MAKEFILE_DIR)/api/contract.mk
else ifeq ($(API_MODE),live-contract)
include $(API_MAKEFILE_DIR)/api/live-contract.mk
else ifeq ($(API_MODE),freeze)
include $(API_MAKEFILE_DIR)/api/freeze.mk
else
$(error Unsupported API_MODE '$(API_MODE)'; expected contract, live-contract, or freeze)
endif
