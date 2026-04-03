# Repo hygiene (keep the workspace REUSE-clean and releaseable)

RM ?= rm -rf

.PHONY: hygiene hygiene-check

hygiene:
	@echo "→ Repo hygiene (bytecode/caches/macOS junk)"
	@# bytecode + caches
	@find . -type d -name '__pycache__' -prune -exec $(RM) {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '*.pyo' -delete 2>/dev/null || true
	@$(RM) .pytest_cache .ruff_cache .mypy_cache .pytype .hypothesis .benchmarks || true
	@$(RM) config/.ruff_cache || true
	@# macOS / IDE junk
	@find . -name '__MACOSX' -prune -exec $(RM) {} + 2>/dev/null || true
	@find . -name '.DS_Store' -delete 2>/dev/null || true
	@$(RM) .idea || true
	@echo "✔ hygiene complete"

hygiene-check:
	@set -euo pipefail; \
	  BAD=$$(find . \( -name '__pycache__' -o -name '*.pyc' -o -name '*.pyo' -o -name '__MACOSX' -o -name '.DS_Store' \) | head -n 50); \
	  if [ -n "$$BAD" ]; then \
	    echo "✘ hygiene-check failed: forbidden files present:"; \
	    echo "$$BAD"; \
	    exit 2; \
	  fi; \
	  echo "✔ hygiene-check passed"

##@ Hygiene
hygiene: ## Remove bytecode/caches/macOS junk that breaks REUSE and releases
hygiene-check: ## Fail if bytecode/caches/macOS junk exist in the workspace
