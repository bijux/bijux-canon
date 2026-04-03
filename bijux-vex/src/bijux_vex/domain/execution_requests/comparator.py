# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.execution_result import ExecutionResult
from bijux_vex.core.types import Result
from bijux_vex.domain.execution_requests.compare import (
    VectorExecutionDiff,
    compare_executions,
)


class ExecutionComparator:
    def compare(
        self,
        execution_a: ExecutionResult,
        results_a: list[Result],
        execution_b: ExecutionResult,
        results_b: list[Result],
    ) -> VectorExecutionDiff:
        return compare_executions(execution_a, results_a, execution_b, results_b)


__all__ = ["ExecutionComparator"]
