# SPDX-License-Identifier: MIT

.PHONY: fmt

fmt: | $(VENV)
	@echo "→ Formatting (ruff format)"
	@$(ACT)/ruff format --config $(CONFIG_DIR)/ruff.toml src tests scripts
