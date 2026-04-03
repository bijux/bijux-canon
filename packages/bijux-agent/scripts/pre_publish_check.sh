#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

echo "→ Running pre-publish checks"
make test lint quality security api sbom docs
