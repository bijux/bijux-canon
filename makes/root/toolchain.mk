# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

root-check-env: pyproject.toml uv.lock $(ROOT_CHECK_STAMP)

$(ROOT_CHECK_STAMP): pyproject.toml uv.lock
	@mkdir -p "$(ROOT_ARTIFACTS_DIR)"
	@rm -rf "$(ROOT_CHECK_VENV)"
	@$(UV_SYNC)
	@touch "$(ROOT_CHECK_STAMP)"

##@ Repository
root-check-env: ## Create or refresh the shared root check environment
