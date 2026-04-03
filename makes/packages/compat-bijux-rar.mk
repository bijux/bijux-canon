PACKAGE_PROFILE_MAKEFILE := $(abspath $(lastword $(MAKEFILE_LIST)))
PACKAGE_MAKEFILE_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PROJECT_SLUG := compat-bijux-rar
PUBLISH_PACKAGE_NAME := bijux-rar

include $(PACKAGE_MAKEFILE_DIR)/compat-package.mk
