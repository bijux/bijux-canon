# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

HELP_DEFINE_TARGET ?= 1
HELP_TARGET ?= help
HELP_FILES ?= $(MAKEFILE_LIST)
HELP_WIDTH ?= 20

ifeq ($(HELP_DEFINE_TARGET),1)
$(HELP_TARGET):
	@awk 'BEGIN{FS=":.*##"; OFS="";} \
	  /^##@/ {gsub(/^##@ */,""); print "\n\033[1m" $$0 "\033[0m"; next} \
	  /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-$(HELP_WIDTH)s\033[0m %s\n", $$1, $$2}' \
	  $(HELP_FILES)
.PHONY: $(HELP_TARGET)
endif
