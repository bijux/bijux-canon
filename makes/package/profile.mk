# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

PACKAGE_PROFILE_MAKEFILE ?= $(abspath $(lastword $(MAKEFILE_LIST)))
PACKAGE_MAKEFILE_DIR ?= $(abspath $(dir $(PACKAGE_PROFILE_MAKEFILE)))
PROJECT_SLUG ?= $(basename $(notdir $(PACKAGE_PROFILE_MAKEFILE)))

include $(PACKAGE_MAKEFILE_DIR)/../env.mk
include $(ROOT_MAKE_DIR)/package/path-sets.mk
