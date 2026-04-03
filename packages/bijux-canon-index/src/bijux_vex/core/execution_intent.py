# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from enum import Enum


class ExecutionIntent(Enum):
    EXACT_VALIDATION = "exact_validation"
    REPRODUCIBLE_RESEARCH = "reproducible_research"
    EXPLORATORY_SEARCH = "exploratory_search"
    PRODUCTION_RETRIEVAL = "production_retrieval"


__all__ = ["ExecutionIntent"]
