# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

HELP_DEFINE_TARGET ?= 1
HELP_TARGET ?= help
HELP_FILES ?= $(MAKEFILE_LIST)
HELP_WIDTH ?= 20

ifeq ($(HELP_DEFINE_TARGET),1)
$(HELP_TARGET):
	@awk 'BEGIN{FS=":.*##"; OFS=""; section=""} \
	  function add_section(name) { \
	    if (!(name in section_seen)) { \
	      section_seen[name] = 1; \
	      section_order[++section_count] = name; \
	    } \
	  } \
	  /^##@/ { \
	    gsub(/^##@ */,""); \
	    section = $$0; \
	    add_section(section); \
	    next; \
	  } \
	  /^[a-zA-Z0-9_.-]+:.*##/ { \
	    if (section == "") { \
	      section = "General"; \
	      add_section(section); \
	    } \
	    section_lines[section] = section_lines[section] sprintf("  \033[36m%-$(HELP_WIDTH)s\033[0m %s\n", $$1, $$2); \
	  } \
	  END { \
	    for (i = 1; i <= section_count; i++) { \
	      name = section_order[i]; \
	      if (section_lines[name] == "") { \
	        continue; \
	      } \
	      if (printed_any) { \
	        print ""; \
	      } \
	      print "\033[1m" name "\033[0m"; \
	      printf "%s", section_lines[name]; \
	      printed_any = 1; \
	    } \
	  }' \
	  $(HELP_FILES)
.PHONY: $(HELP_TARGET)
endif
