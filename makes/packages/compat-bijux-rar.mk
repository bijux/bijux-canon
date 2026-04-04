include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk

PUBLISH_PACKAGE_NAME := bijux-rar

include $(PACKAGE_MAKEFILE_DIR)/compat-package.mk
