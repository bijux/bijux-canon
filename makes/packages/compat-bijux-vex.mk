PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk

PUBLISH_PACKAGE_NAME := bijux-vex

include $(PACKAGE_MAKEFILE_DIR)/compat-package.mk
