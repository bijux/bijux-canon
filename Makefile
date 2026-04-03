PACKAGES := agentic-flows bijux-agent bijux-rag bijux-rar bijux-vex
PACKAGE ?=

.DEFAULT_GOAL := help
.PHONY: help list test lint quality security docs api build sbom all clean

define run_target
	@set -e; \
	if [ -n "$(PACKAGE)" ]; then \
	  echo "==> $(PACKAGE): $(1)"; \
	  $(MAKE) -C packages/$(PACKAGE) $(1); \
	else \
	  for package in $(PACKAGES); do \
	    echo "==> $$package: $(1)"; \
	    $(MAKE) -C packages/$$package $(1); \
	  done; \
	fi
endef

help:
	@printf "%s\n" \
	  "Targets:" \
	  "  list      List package slugs" \
	  "  test      Run package tests" \
	  "  lint      Run package lint checks" \
	  "  quality   Run package quality checks" \
	  "  security  Run package security checks" \
	  "  docs      Build package docs" \
	  "  api       Run package API checks" \
	  "  build     Build package artifacts" \
	  "  sbom      Generate package SBOMs" \
	  "  clean     Clean package artifacts" \
	  "  all       Run test, lint, quality, security, docs, api, build, sbom" \
	  "" \
	  "Use PACKAGE=<slug> to scope a target to one package."

list:
	@printf "%s\n" $(PACKAGES)

test:
	$(call run_target,test)

lint:
	$(call run_target,lint)

quality:
	$(call run_target,quality)

security:
	$(call run_target,security)

docs:
	$(call run_target,docs)

api:
	$(call run_target,api)

build:
	$(call run_target,build)

sbom:
	$(call run_target,sbom)

clean:
	$(call run_target,clean)

all: test lint quality security docs api build sbom
