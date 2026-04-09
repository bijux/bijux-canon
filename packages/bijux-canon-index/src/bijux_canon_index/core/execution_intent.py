# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Execution intent helpers for core logic."""

from __future__ import annotations

from enum import Enum


class ExecutionIntent(Enum):
    """Enumeration of execution intent."""
    EXACT_VALIDATION = "exact_validation"
    REPRODUCIBLE_RESEARCH = "reproducible_research"
    EXPLORATORY_SEARCH = "exploratory_search"
    PRODUCTION_RETRIEVAL = "production_retrieval"


__all__ = ["ExecutionIntent"]
