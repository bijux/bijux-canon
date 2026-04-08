API_MODE ?= contract
API_REPO_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/api

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/bijux-py/api.mk
