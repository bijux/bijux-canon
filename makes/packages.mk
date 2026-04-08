ROOT_PACKAGE_PROFILE_DIR ?= $(ROOT_MAKEFILE_DIR)/packages

PACKAGE_ALIASES := \
	agentic-flows=bijux-canon-runtime \
	bijux-agent=bijux-canon-agent \
	bijux-rag=bijux-canon-ingest \
	bijux-rar=bijux-canon-reason \
	bijux-vex=bijux-canon-index

PRIMARY_PACKAGE_RECORDS := \
	bijux-canon-dev|primary,check,buildable,sbom,test,api_profile_off|bijux-canon-dev.mk \
	bijux-canon-runtime|primary,check,buildable,sbom,test,api|bijux-canon-runtime.mk \
	bijux-canon-agent|primary,check,buildable,sbom,test,api|bijux-canon-agent.mk \
	bijux-canon-ingest|primary,check,buildable,sbom,test,api|bijux-canon-ingest.mk \
	bijux-canon-reason|primary,check,buildable,sbom,test,api|bijux-canon-reason.mk \
	bijux-canon-index|primary,check,buildable,sbom,test,api|bijux-canon-index.mk

COMPAT_PACKAGE_RECORDS := \
	compat-agentic-flows|compat,check|compat-package.mk \
	compat-bijux-agent|compat,check|compat-package.mk \
	compat-bijux-rag|compat,check|compat-package.mk \
	compat-bijux-rar|compat,check|compat-package.mk \
	compat-bijux-vex|compat,check|compat-package.mk

PACKAGE_RECORDS := $(PRIMARY_PACKAGE_RECORDS) $(COMPAT_PACKAGE_RECORDS)

include $(ROOT_MAKEFILE_DIR)/bijux-py/package-catalog.mk
