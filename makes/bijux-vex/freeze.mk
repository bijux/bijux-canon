# SPDX-License-Identifier: MIT

freeze-dry-run: ## Run freeze dry-run checks
	@echo "→ Running freeze dry run"
	@FREEZE_DRY_RUN=1 $(MAKE) lint test quality security
	@$(ACT)/pytest tests/unit/test_freeze_guard.py

