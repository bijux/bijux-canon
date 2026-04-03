# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""Contracts describing how other bijux systems integrate with VEX."""

from __future__ import annotations

VEX_ECOSYSTEM_CONTRACT = {
    "version": "1.0",
    "bijux_rar": {
        "relies_on": ("execution_id", "execution_signature", "replayable"),
        "must_not_reimplement": ("execution_contract", "provenance_lineage"),
    },
    "bijux_rag": {
        "relies_on": ("execution_contract", "execution_plan"),
        "must_not_reimplement": ("approximation_report",),
    },
}


__all__ = ["VEX_ECOSYSTEM_CONTRACT"]
