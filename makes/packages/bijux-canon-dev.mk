include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/../package/profile.mk
include $(ROOT_MAKE_DIR)/package/canon-python.mk

PACKAGE_IMPORT_NAME := bijux_canon_dev
SECURITY_IGNORE_IDS := PYSEC-2022-42969
SKIP_MYPY         := 1
ENABLE_CODESPELL  := 1
ENABLE_MYPY       := 0
ENABLE_RADON      := 0
ENABLE_PYDOCSTYLE := 0
BUILD_CHECK_DISTS := 1
PACKAGE_ALL_TARGETS := clean install test lint quality security build sbom

include $(ROOT_MAKE_DIR)/package/gates.mk
