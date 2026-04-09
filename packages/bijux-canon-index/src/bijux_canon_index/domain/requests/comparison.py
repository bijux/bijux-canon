# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Comparison helpers for domain logic."""

from __future__ import annotations

from bijux_canon_index.core.execution_result import ExecutionResult
from bijux_canon_index.core.types import Result
from bijux_canon_index.domain.requests.execution_diff import (
    VectorExecutionDiff,
    compare_executions,
)


class ExecutionComparator:
    """Represents execution comparator."""
    def compare(
        self,
        execution_a: ExecutionResult,
        results_a: list[Result],
        execution_b: ExecutionResult,
        results_b: list[Result],
    ) -> VectorExecutionDiff:
        """Compare execution a."""
        return compare_executions(execution_a, results_a, execution_b, results_b)


__all__ = ["ExecutionComparator"]
