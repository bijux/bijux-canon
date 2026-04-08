SBOM_VERSION_RESOLVER ?= -m bijux_canon_dev.release.version_resolver
SBOM_REQUIREMENTS_WRITER ?= -m bijux_canon_dev.sbom.requirements_writer

include $(abspath $(dir $(lastword $(MAKEFILE_LIST))))/bijux-py/sbom.mk
