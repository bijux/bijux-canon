DOCS_CONFIG_CLI ?= -m bijux_canon_dev.docs.mkdocs_config

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/bijux-py/docs.mk
