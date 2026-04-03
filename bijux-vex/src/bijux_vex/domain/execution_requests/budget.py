# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable

from bijux_vex.core.errors import BudgetExceededError
from bijux_vex.core.execution_result import (
    ApproximationReport,
    ExecutionCost,
    ExecutionStatus,
)
from bijux_vex.core.types import ExecutionBudget, ExecutionRequest, Result


def ann_budget_to_params(budget: ExecutionRequest | None) -> dict[str, int | float]:
    """Map execution budget to ANN parameters deterministically."""
    if budget is None or budget.execution_budget is None:
        return {}
    params: dict[str, int | float] = {}
    if budget.execution_budget.max_ann_probes is not None:
        params["ef_search"] = int(budget.execution_budget.max_ann_probes)
    if budget.execution_budget.max_error is not None:
        params["epsilon"] = float(budget.execution_budget.max_error)
    if budget.execution_budget.max_vectors is not None:
        params["truncate"] = int(budget.execution_budget.max_vectors)
    return params


def default_budget(request: ExecutionRequest) -> dict[str, int | float]:
    return normalize_budget(request.execution_budget)


def normalize_budget(
    execution_budget: ExecutionBudget | None,
) -> dict[str, int | float]:
    """Return a canonical budget mapping for downstream use."""
    budget: dict[str, int | float] = {}
    if execution_budget:
        if execution_budget.max_latency_ms is not None:
            budget["max_latency_ms"] = execution_budget.max_latency_ms
        if execution_budget.max_memory_mb is not None:
            budget["max_memory_mb"] = execution_budget.max_memory_mb
        if execution_budget.max_error is not None:
            budget["max_error"] = execution_budget.max_error
        if execution_budget.max_vectors is not None:
            budget["max_vectors"] = execution_budget.max_vectors
        if execution_budget.max_distance_computations is not None:
            budget["max_distance_computations"] = (
                execution_budget.max_distance_computations
            )
        if execution_budget.max_ann_probes is not None:
            budget["max_ann_probes"] = execution_budget.max_ann_probes
    return budget


def check_budget(
    budget: dict[str, int | float] | None,
    counters: dict[str, int],
    partial_results: Iterable[Result],
) -> None:
    if not budget:
        return
    if budget.get("max_vectors") is not None and counters["vectors"] > int(
        budget["max_vectors"]
    ):
        raise BudgetExceededError(
            message="max vectors budget exhausted",
            dimension="vectors",
            partial_results=tuple(partial_results),
        )
    if budget.get("max_distance_computations") is not None and counters[
        "distance"
    ] > int(budget["max_distance_computations"]):
        raise BudgetExceededError(
            message="distance budget exhausted",
            dimension="distance",
            partial_results=tuple(partial_results),
        )
    if budget.get("max_ann_probes") is not None and counters["ann_probes"] > int(
        budget["max_ann_probes"]
    ):
        raise BudgetExceededError(
            message="ANN probes budget exhausted",
            dimension="ann_probes",
            partial_results=tuple(partial_results),
        )
    # Simple deterministic enforcement for latency/memory using counter proxies.
    if budget.get("max_latency_ms") is not None and counters["vectors"] > int(
        budget["max_latency_ms"]
    ):
        raise BudgetExceededError(
            message="latency budget exhausted",
            dimension="latency",
            partial_results=tuple(partial_results),
        )
    if budget.get("max_memory_mb") is not None and counters["distance"] > int(
        budget["max_memory_mb"]
    ):
        raise BudgetExceededError(
            message="memory budget exhausted",
            dimension="memory",
            partial_results=tuple(partial_results),
        )


def apply_budget_outcomes(
    request: ExecutionRequest,
    approximation: ApproximationReport | None,
    cost: ExecutionCost,
    status: ExecutionStatus,
    failure_reason: str | None,
) -> tuple[ExecutionStatus, str | None]:
    if not request.execution_budget:
        return status, failure_reason
    if (
        request.execution_budget.max_latency_ms is not None
        and cost.wall_time_estimate_ms > request.execution_budget.max_latency_ms
    ):
        status = ExecutionStatus.PARTIAL
        failure_reason = failure_reason or "budget_exhausted_latency"
    if (
        request.execution_budget.max_memory_mb is not None
        and cost.vector_reads > request.execution_budget.max_memory_mb
    ):
        status = ExecutionStatus.PARTIAL
        failure_reason = failure_reason or "budget_exhausted_memory"
    if (
        request.execution_budget.max_error is not None
        and approximation
        and approximation.distance_error > request.execution_budget.max_error
    ):
        status = ExecutionStatus.PARTIAL
        failure_reason = failure_reason or "budget_exhausted_error"
    if approximation and approximation.recall_at_k < 0.1:
        status = ExecutionStatus.PARTIAL
        failure_reason = failure_reason or "recall_below_bound"
    return status, failure_reason
