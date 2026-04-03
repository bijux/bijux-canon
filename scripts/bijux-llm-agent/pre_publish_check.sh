#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
set -euo pipefail

MONOREPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${MONOREPO_ROOT}/packages/bijux-llm-agent"

echo "→ Running pre-publish checks"
make test lint quality security api sbom docs
